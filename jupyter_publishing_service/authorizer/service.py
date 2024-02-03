from fastapi import Request
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException

from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.models import Permission

httpBearer = HTTPBearer()

# singleton scoped to the module
authorizer_service_global = None


def set_authorizer_class(authorizer_class: AuthorizerABC):
    global authorizer_service_global
    authorizer_service_global = authorizer_class


async def require_read_permissions(request: Request):
    permissions = [Permission(name="READ")]
    request.state.permissions = permissions


async def require_read_write_permissions(request: Request):
    permissions = [Permission(name="READ"), Permission(name="WRITE")]
    request.state.permissions = permissions


async def authorize(request: Request):
    user = request.state.user
    permissions = request.state.permissions
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    action = request.method.lower()
    data = await request.json() if action in ["post", "put"] else {}
    resource_name = request.url.path.strip("/").split("/")[1]
    file_id = data.get("id") if action in ["post", "put"] else resource_name
    data["permissions"] = permissions
    data["file_id"] = file_id
    allowed = await authorizer_service_global.authorize(user, data)
    if not allowed:
        raise HTTPException(status_code=403, detail="Not authorized")
    return True
