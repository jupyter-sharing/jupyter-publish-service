from fastapi import Depends
from sqlmodel import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.database.manager import get_session
from jupyter_publishing_service.models import CollaboratorRole, PermissionRoleLink
from jupyter_publishing_service.traits import UnicodeFromEnv


class RBACAuthorizer(LoggingConfigurable):
    email_claim = UnicodeFromEnv(
        name=constants.EMAIL_CLAIM_STRING,
        help="key denoting email claim in the JWT. Email address is assumed to be unique",
        default="email",
        allow_none=True,
    ).tag(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = get_session

    async def authorize(self, user, data) -> bool:
        async with self._session() as session:
            email = user.get(self.email_claim)
            required_perms = [perm.name for perm in data["permissions"]]
            file_id = data["file_id"]
            c_stmt = (
                select(CollaboratorRole.role)
                .where(CollaboratorRole.file == file_id)
                .where(CollaboratorRole.email == email)
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
            return False


AuthorizerABC.register(RBACAuthorizer)
