import uuid
from typing import List

from fastapi import Depends
from sqlmodel import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.collaborator.abc import CollaboratorStore
from jupyter_publishing_service.collaborator.helper import (
    create_or_update_collaborator,
    create_or_update_file,
    create_or_update_role,
)
from jupyter_publishing_service.database.manager import get_session
from jupyter_publishing_service.models import (
    Collaborator,
    CollaboratorRole,
    Role,
    SharedFile,
    SharedFileWithCollaborators,
)


class SQLCollaboratorProvider(LoggingConfigurable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = get_session

    async def add(self, collaborator: Collaborator, file: SharedFile, roles: List[Role]):
        async with self._session() as session:
            await create_or_update_collaborator(session, collaborator)
            await create_or_update_file(session, file)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file.id, role=role.name
                )
                await create_or_update_role(session, collab_role)
            await session.commit()

    async def delete(self, collaborator: Collaborator, file: SharedFile):
        async with self._session() as session:
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
        async with self._session() as session:
            await create_or_update_collaborator(session, collaborator)
            await create_or_update_file(session, file)
            for role in roles:
                collab_role = CollaboratorRole(
                    email=collaborator.email, file=file.id, role=role.name
                )
                await create_or_update_role(session, collab_role)

    async def get(self, file: uuid.UUID) -> SharedFileWithCollaborators:
        async with self._session() as session:
            c_stmt = select(CollaboratorRole).where(CollaboratorRole.file == file)
            results = await session.exec(c_stmt)
            collab_roles = results.all()
            f_stmt = select(SharedFile).where(SharedFile.id == file)
            results = await session.exec(f_stmt)
            shared_file = results.first()
            result = SharedFileWithCollaborators(
                file=shared_file, collaborators=collab_roles, content=None
            )
            return result


CollaboratorStore.register(SQLCollaboratorProvider)
