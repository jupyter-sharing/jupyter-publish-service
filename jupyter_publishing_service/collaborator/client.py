from typing import List

from sqlmodel import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.collaborator.abc import CollaboratorStore
from jupyter_publishing_service.models import (
    Collaborator,
    CollaboratorRole,
    Role,
    SharedFile,
)
from jupyter_publishing_service.session.helper import (
    create_or_update_collaborator,
    create_or_update_file,
    create_or_update_role,
)
from jupyter_publishing_service.session.manager import SessionManager


class SQLCollaboratorProvider(LoggingConfigurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_manager = SessionManager()

    async def add(self, collaborator: Collaborator, file: SharedFile, roles: List[Role]):
        async with self._session_manager.get_session() as session:
            await create_or_update_collaborator(session, collaborator)
            await create_or_update_file(session, file)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file.id, role=role.name
                )
                await create_or_update_role(session, collab_role)
            await session.commit()

    async def delete(self, collaborator: Collaborator, file: SharedFile):
        async with self._session_manager.get_session() as session:
            statement = (
                select(CollaboratorRole)
                .where(CollaboratorRole.email == collaborator.email)
                .where(CollaboratorRole.file == file.id)
            )
            results = await session.exec(statement)
            for collab_role in results:
                session.delete(collab_role)
            await session.commit()

    async def update(self, collaborator: Collaborator, file: SharedFile, roles: List[Role]):
        async with self._session_manager.get_session as session:
            await create_or_update_collaborator(session, collaborator)
            await create_or_update_file(session, file)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file.id, role=role.name
                )
                await create_or_update_role(session, collab_role)

    async def get(self, file: SharedFile) -> list[CollaboratorRole]:
        async with self._session_manager.get_session as session:
            statement = select(CollaboratorRole).where(CollaboratorRole.file == file.id)
            results = await session.exec(statement)
            collab_roles = results.scalars().all()
            return collab_roles


CollaboratorStore.register(SQLCollaboratorProvider)
