from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.models.sql import Collaborator, PermissionRoleLink, User
from jupyter_publishing_service.traits import UnicodeFromEnv


class SQLRoleBasedAuthorizer(LoggingConfigurable):
    async def authorize(self, user: User, action: str, file_id: str) -> bool:

        async with self.parent.get_session() as session:
            # Find this users collaborative roles.
            c_stmt = (
                select(Collaborator.role)
                .where(Collaborator.file == file_id)
                .where(Collaborator.username == user.username)
            )
            results = await session.exec(c_stmt)
            roles = results.all()

            # Getch permissions for this role.
            r_stmt = select(PermissionRoleLink.permission_name).where(
                PermissionRoleLink.role_name.in_(roles)
            )
            results = await session.exec(r_stmt)
            role_permissions = results.all()
            # Is this action allowed by these permissions
            if action in role_permissions:
                return True
            return False


AuthorizerABC.register(SQLRoleBasedAuthorizer)
