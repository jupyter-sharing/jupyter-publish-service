from sqlmodel import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models import (
    Collaborator,
    CollaboratorRole,
    Role,
    SharedFile,
)
from jupyter_publishing_service.session.manager import SessionManager


class SQLCollaboratorProvider(LoggingConfigurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_manager = SessionManager()

    async def add(self, user: Collaborator, file: SharedFile, roles: list[Role]):
        async with self._session_manager.get_session() as session:
            session.add(user)
            session.add(file)
            for role in roles:
                collab_role = CollaboratorRole(email=user.email, file=file.id, role=role.name)
                session.add(collab_role)
            await session.commit()

    async def delete(self, user: Collaborator, file: SharedFile):
        async with self._session_manager.get_session() as session:
            statement = (
                select(CollaboratorRole)
                .where(CollaboratorRole.email == user.email)
                .where(CollaboratorRole.file == file.id)
            )
            results = await session.exec(statement)
            for collab_role in results:
                session.delete(collab_role)
            await session.commit()

    async def update(self, user: Collaborator, file: SharedFile, roles: list[Role]):
        async with self._session_manager.get_session as session:
            session.add(user)
            session.add(file)
            for role in roles:
                collab_role = CollaboratorRole(email=user.email, file=file.id, role=role.name)
                session.add(collab_role)
            await session.commit()

    async def get(self, file: SharedFile) -> list[CollaboratorRole]:
        async with self._session_manager.get_session as session:
            statement = select(CollaboratorRole).where(CollaboratorRole.file == file.id)
            results = await session.exec(statement)
            collab_roles = results.scalars().all()
            return collab_roles
