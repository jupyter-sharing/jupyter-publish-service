from typing import List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.collaborator.abc import CollaboratorStoreABC
from jupyter_publishing_service.models.sql import Collaborator, CollaboratorRole, Role


async def create_or_update_collaborator(session, collaborator: Collaborator):
    current_collaborator = await session.get(Collaborator, collaborator.email)
    if current_collaborator is None:
        current_collaborator = collaborator
    setattr(current_collaborator, "name", collaborator.name)
    session.add(current_collaborator)
    await session.commit()
    await session.refresh(current_collaborator)
    return current_collaborator


async def create_or_update_role(session, role: CollaboratorRole):
    statement = (
        select(CollaboratorRole)
        .where(CollaboratorRole.email == role.email)
        .where(CollaboratorRole.file == role.file)
        .where(CollaboratorRole.role == role.role)
    )
    result = await session.exec(statement)
    current_role = result.first()
    if current_role is None:
        current_role = role
    for key, val in role.model_dump(exclude_unset=True).items():
        setattr(current_role, key, val)
    session.add(current_role)
    await session.commit()
    return current_role


class SQLCollaboratorStore(LoggingConfigurable):
    async def get(self, file_id: str) -> List[CollaboratorRole]:
        async with self.parent.get_session() as session:
            c_stmt = select(CollaboratorRole).where(CollaboratorRole.file == file_id)
            results = await session.exec(c_stmt)
            collab_roles = results.all()
            return collab_roles

    async def add(self, file_id: str, collaborator: Collaborator, roles: List[Role]):
        async with self.parent.get_session() as session:
            await create_or_update_collaborator(session, collaborator)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file_id, role=role.name
                )
                await create_or_update_role(session, collab_role)
            await session.commit()

    async def delete(self, file_id: str, collaborator: Collaborator):
        async with self.parent.get_session() as session:
            statement = (
                select(CollaboratorRole)
                .where(CollaboratorRole.email == collaborator.email)
                .where(CollaboratorRole.file == file_id)
            )
            results = await session.exec(statement)
            for collab_role in results:
                await session.delete(collab_role)
            await session.commit()

    async def update(self, file_id: str, collaborator: Collaborator, roles: List[Role]):
        async with self.parent.get_session() as session:
            await create_or_update_collaborator(session, collaborator)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file_id, role=role.name
                )
                await create_or_update_role(session, collab_role)

    async def list(self, user_id: str) -> List[str]:
        """List all files that a collaborator has access to."""
        session: AsyncSession
        async with self.parent.get_session() as session:
            statement = select(CollaboratorRole.file).where(CollaboratorRole.email == user_id)
            results = await session.exec(statement)
            file_ids = results.fetchall()
            return file_ids

    async def search(self, substring) -> List[Collaborator]:
        """Search a list of collaborators."""
        pass


CollaboratorStoreABC.register(SQLCollaboratorStore)
