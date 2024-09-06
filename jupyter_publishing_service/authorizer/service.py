from fastapi import Request
from fastapi.security import HTTPBearer

from jupyter_publishing_service.models.sql import Permission

httpBearer = HTTPBearer()


async def require_read_permissions(request: Request):
    permissions = [Permission(name="READ")]
    request.state.permissions = permissions


async def require_read_write_permissions(request: Request):
    permissions = [Permission(name="READ"), Permission(name="WRITE")]
    request.state.permissions = permissions
