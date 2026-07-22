from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.models.sql import Collaborator, PermissionRoleLink, User


class SQLRoleBasedAuthorizer(LoggingConfigurable):
    async def authorize(self, user: User, action: str, file_id: str) -> bool:
        async with self.parent.get_session() as session:
            # Find this user's collaborative roles on this file.
            c_stmt = (
                select(Collaborator.role)
                .where(Collaborator.file == file_id)
                .where(Collaborator.authority == user.authority)
                .where(Collaborator.username == user.username)
            )
            results = await session.exec(c_stmt)
            roles = results.all()

            # Fetch permissions for these roles.
            r_stmt = select(PermissionRoleLink.permission_name).where(
                PermissionRoleLink.role_name.in_(roles)
            )
            results = await session.exec(r_stmt)
            role_permissions = results.all()
            return action in role_permissions


AuthorizerABC.register(SQLRoleBasedAuthorizer)
