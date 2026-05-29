from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException

from ._version import __version__
from .models.rest import (
    ServiceStatusResponse,
    SharedFileRequestModel,
    SharedFileResponseModel,
)
from .models.sql import User
from .storage.base import BaseStorageManager

httpBearer = HTTPBearer()

router = APIRouter()

HTTP_VERB_TO_AUTH = {"get": "READ", "post": "WRITE", "patch": "WRITE", "delete": "WRITE"}


async def authenticate(request: Request) -> User:
    """Resolve the request's authority, validate the bearer token, and
    attach the resulting User and bound authority to request.state."""
    credentials = await httpBearer(request)
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=403, detail="Unsupported authentication method")
    bound = router.app.authority_registry.resolve(request)
    user = await bound.authenticator.authenticate(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    request.state.user = user  # type: ignore[attr-defined]
    request.state.authority = bound  # type: ignore[attr-defined]
    return user


async def authorize(request: Request, file_id: str):
    user: User = request.state.user
    storage_manager: BaseStorageManager = router.app.storage_manager
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    verb = request.method.lower()
    action = HTTP_VERB_TO_AUTH[verb]
    allowed = await storage_manager.authorization_store.authorize(user, action, file_id)
    if not allowed:
        raise HTTPException(status_code=403, detail="Not authorized")
    return True


@asynccontextmanager
async def lifespan(app):
    storage_manager: BaseStorageManager = router.app.storage_manager
    await storage_manager.start()
    yield


@router.get("/", response_model=ServiceStatusResponse)
async def service_status():
    """Check the status and health of service."""
    return ServiceStatusResponse(version=__version__, status="healthy")


@router.get(
    "/sharing",
    dependencies=[Depends(authenticate)],
    response_model=List[SharedFileResponseModel],
)
async def list_files(request: Request):
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.list(request.state.user)


@router.get(
    "/sharing/users",
    dependencies=[Depends(authenticate)],
)
async def search_users(request: Request, substring: Optional[str] = None) -> List[User]:
    return await request.state.authority.user_store.search_users(substring)


@router.get(
    "/sharing/{file_id}",
    dependencies=[Depends(authenticate), Depends(authorize)],
    response_model=SharedFileResponseModel,
)
async def get_file(
    file_id: str,
    request: Request,
    contents: bool = False,
    collaborators: bool = False,
) -> SharedFileResponseModel:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.get(file_id, contents=contents, collaborators=collaborators)


@router.post(
    "/sharing",
    dependencies=[Depends(authenticate)],
    response_model=SharedFileResponseModel,
)
async def add_file(body: SharedFileRequestModel) -> SharedFileResponseModel:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.add(body)


@router.patch(
    "/sharing/{file_id}",
    dependencies=[
        Depends(authenticate),
        Depends(authorize),
    ],
    response_model=SharedFileResponseModel,
)
async def update_file(file_id: str, body: SharedFileRequestModel) -> SharedFileResponseModel:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.update(file_id, body)


@router.delete(
    "/sharing/{file_id}",
    dependencies=[
        Depends(authenticate),
        Depends(authorize),
    ],
)
async def delete_file(file_id: str):
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.delete(file_id)
