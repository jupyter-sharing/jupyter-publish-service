from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from starlette.exceptions import HTTPException

from ._version import __version__
from .authenticator.service import authenticate
from .authorizer.service import require_read_permissions, require_read_write_permissions
from .models.rest import (
    Collaborator,
    ServiceStatusResponse,
    SharedFileRequestModel,
    SharedFileResponseModel,
)
from .models.sql import Collaborator
from .storage.base import BaseStorageManager

router = APIRouter()


async def authorize(request: Request):
    user = request.state.user
    permissions = request.state.permissions
    storage_manager: BaseStorageManager = router.app.storage_manager
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    action = request.method.lower()
    data = await request.json() if action in ["post", "put"] else {}
    resource_name = request.url.path.strip("/").split("/")[1]
    file_id = data.get("id") if action in ["post", "put"] else resource_name
    data["permissions"] = permissions
    data["file_id"] = file_id
    allowed = await storage_manager.authorization_store.authorize(user, data)
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
async def list_files(
    request: Request,
):
    storage_manager: BaseStorageManager = router.app.storage_manager
    user = request.state.user
    return await storage_manager.list(user["name"])


@router.get(
    "/sharing/users",
    dependencies=[
        Depends(authenticate),
    ],
)
async def search_users(substring: Optional[str] = None) -> List[Collaborator]:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.search_users(substring)


@router.get(
    "/sharing/{file_id}",
    dependencies=[Depends(authenticate), Depends(require_read_permissions), Depends(authorize)],
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
    response_model=SharedFileResponseModel,
)
async def add_file(body: SharedFileRequestModel) -> SharedFileResponseModel:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.add(body)


@router.patch(
    "/sharing/{file_id}",
    dependencies=[
        Depends(authenticate),
        Depends(require_read_write_permissions),
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
        Depends(require_read_write_permissions),
        Depends(authorize),
    ],
)
async def delete_file(file_id: str):
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.delete(file_id)
