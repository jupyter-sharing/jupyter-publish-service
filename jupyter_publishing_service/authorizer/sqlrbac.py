from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.models.sql import (
    CollaboratorRole,
    PermissionRoleLink,
    SharedFileMetadata,
)
from jupyter_publishing_service.traits import UnicodeFromEnv


class SQLRoleBasedAuthorizer(LoggingConfigurable):
    async def authorize(self, user, data) -> bool:
        session: AsyncSession
        async with self.parent.get_session() as session:
            name = user.get("name")
            required_perms = [perm.name for perm in data["permissions"]]
            file_id = data["file_id"]
            c_stmt = (
                select(CollaboratorRole.role)
                .where(CollaboratorRole.file == file_id)
                .where(CollaboratorRole.name == name)
            )
            results = await session.exec(c_stmt)
            roles = results.all()
            r_stmt = select(PermissionRoleLink.permission_name).where(
                PermissionRoleLink.role_name.in_(roles)
            )
            results = await session.exec(r_stmt)
            user_permissions = results.all()
            if all(perms in user_permissions for perms in required_perms):
                return True

            c_stmt = select(SharedFileMetadata.id).where(CollaboratorRole.id == file_id)
            results = await session.exec(c_stmt)
            item_missing = results.one_or_none() is None
            if item_missing:
                raise HTTPException(status_code=404, detail="The file ID requested does not exist.")
            return False


AuthorizerABC.register(SQLRoleBasedAuthorizer)
