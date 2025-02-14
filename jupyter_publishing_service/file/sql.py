from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.sql import JupyterContentsModel

from .abc import FileStoreABC


async def create_or_update_jupyter_contents(session, file_id: str, file: JupyterContentsModel):
    current_model = await session.get(JupyterContentsModel, file_id)
    if current_model is None:
        current_model = file
    data = file.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(current_model, key, val)
    session.add(current_model)
    await session.commit()
    await session.refresh(current_model)


class SQLFileStore(LoggingConfigurable):
    async def get(self, file_id: str) -> JupyterContentsModel:
        async with self.parent.get_session() as session:
            stmt = select(JupyterContentsModel).where(JupyterContentsModel.id == file_id)
            results = await session.exec(stmt)
            file: JupyterContentsModel = results.first()
            return file

    async def add(self, file_id: str, file: JupyterContentsModel) -> JupyterContentsModel:
        async with self.parent.get_session() as session:
            file.id = file_id
            await create_or_update_jupyter_contents(session, file_id, file)

    async def delete(self, file_id: str):
        session: AsyncSession
        async with self.parent.get_session() as session:
            statement = select(JupyterContentsModel).where(JupyterContentsModel.id == file_id)
            results = await session.exec(statement)
            for result in results:
                await session.delete(result)
            await session.commit()

    async def update(self, file_id: str, file: JupyterContentsModel):
        async with self.parent.get_session() as session:
            file.id = file_id
            await create_or_update_jupyter_contents(session, file_id, file)


# Register this class a virtual subclass
# to pass instance check when used as a traitlet.
FileStoreABC.register(SQLFileStore)
