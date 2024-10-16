from typing import List

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.sql import SharedFileMetadata

from .abc import MetadataStoreABC


async def create_or_update_file(
    session: AsyncSession, metadata: SharedFileMetadata
) -> SharedFileMetadata:
    current_file = await session.get(SharedFileMetadata, metadata.id)
    if current_file is None:
        current_file = metadata
    data = metadata.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(current_file, key, val)
    session.add(current_file)
    await session.commit()
    await session.refresh(current_file)
    return current_file


class SQLMetadataStore(LoggingConfigurable):
    async def add(self, metadata: SharedFileMetadata) -> SharedFileMetadata:
        async with self.parent.get_session() as session:
            shared_file = await create_or_update_file(session, metadata)
            await session.commit()
            return shared_file

    async def delete(self, file_id: str):
        async with self.parent.get_session() as session:
            statement = select(SharedFileMetadata).where(SharedFileMetadata.id == file_id)
            results = await session.exec(statement)
            for collab_role in results:
                await session.delete(collab_role)
            await session.commit()

    async def update(self, metadata: SharedFileMetadata) -> SharedFileMetadata:
        async with self.parent.get_session() as session:
            return await create_or_update_file(session, metadata)

    async def get(self, file_id: str) -> SharedFileMetadata:
        async with self.parent.get_session() as session:
            f_stmt = select(SharedFileMetadata).where(SharedFileMetadata.id == file_id)
            results = await session.exec(f_stmt)
            return results.first()

    async def list(self, list_of_file_ids: List[str]) -> List[SharedFileMetadata]:
        async with self.parent.get_session() as session:
            statement = select(SharedFileMetadata).where(
                col(SharedFileMetadata.id).in_(list_of_file_ids)
            )
            results = await session.exec(statement)
            files = results.fetchall()
            return files


MetadataStoreABC.register(SQLMetadataStore)
