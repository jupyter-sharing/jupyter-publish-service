from typing import List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.collaborator.abc import CollaboratorStoreABC
from jupyter_publishing_service.models.sql import Collaborator, Role, User


async def create_or_update_user(session, user: User) -> User:
    current_user = await session.get(User, user.username)
    if current_user is None:
        current_user = user
    setattr(current_user, "username", user.username)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user


async def create_or_update_collaborator(session, collaborator: Collaborator) -> Collaborator:
    statement = (
        select(Collaborator)
        .where(Collaborator.username == collaborator.username)
        .where(Collaborator.file == collaborator.file)
        .where(Collaborator.role == collaborator.role)
    )
    result = await session.exec(statement)
    current_collaborator = result.first()
    if current_collaborator is None:
        current_collaborator = collaborator
    for key, val in collaborator.model_dump(exclude_unset=True).items():
        setattr(current_collaborator, key, val)
    session.add(current_collaborator)
    await session.commit()
    return current_collaborator


class SQLCollaboratorStore(LoggingConfigurable):
    async def get(self, file_id: str) -> List[Collaborator]:
        async with self.parent.get_session() as session:
            c_stmt = select(Collaborator).where(Collaborator.file == file_id)
            results = await session.exec(c_stmt)
            collab_roles = results.all()
            return collab_roles

    async def add(self, file_id: str, user: User, roles: List[Role]):
        async with self.parent.get_session() as session:
            await create_or_update_user(session, user)
            for role in roles:
                collab_role = Collaborator(username=user.username, file=file_id, role=role.name)
                await create_or_update_collaborator(session, collab_role)
            await session.commit()

    async def delete(self, file_id: str, user: User):
        async with self.parent.get_session() as session:
            statement = (
                select(Collaborator)
                .where(Collaborator.username == user.username)
                .where(Collaborator.file == file_id)
            )
            results = await session.exec(statement)
            for collab_role in results:
                await session.delete(collab_role)
            await session.commit()

    async def update(self, file_id: str, user: User, roles: List[Role]):
        async with self.parent.get_session() as session:
            await create_or_update_user(session, user)
            for role in roles:
                collab_role = Collaborator(name=user.username, file=file_id, role=role.name)
                await create_or_update_collaborator(session, collab_role)

    async def list(self, username: str) -> List[str]:
        """List all files that a collaborator has access to."""
        session: AsyncSession
        async with self.parent.get_session() as session:
            statement = select(Collaborator.file).where(Collaborator.username == username)
            results = await session.exec(statement)
            file_ids = results.fetchall()
            return file_ids

    async def search(self, substring) -> List[User]:
        """Search a list of collaborators."""
        pass


CollaboratorStoreABC.register(SQLCollaboratorStore)
