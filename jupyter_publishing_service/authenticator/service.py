from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException

from jupyter_publishing_service.authenticator.abc import AuthenticatorABC

httpBearer = HTTPBearer()

# singleton scoped to the module
authenticator_service_global = None


def set_authenticator_class(authenticator_class: AuthenticatorABC):
    global authenticator_service_global
    authenticator_service_global = authenticator_class


async def authenticate(request: Request) -> dict:
    credentials = await httpBearer(request)
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=403, detail="Unsupported authentication method")
    data = {"token": credentials.credentials}
    user = await authenticator_service_global.authenticate(data)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    request.state.user = user  # type: ignore
    return user
