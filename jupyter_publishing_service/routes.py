from fastapi import APIRouter, Depends, Request

from ._version import __version__
from .authenticator.service import authenticate
from .authorizer.service import (
    authorize,
    require_read_permissions,
    require_read_write_permissions,
)
from .database.manager import create_db
from .models.rest import (
    ServiceStatusResponse,
    SharedFileRequestModel,
    SharedFileResponseModel,
)
from .storagemanager import BaseStorageManager

router = APIRouter()


@router.on_event("startup")
async def on_startup():
    await create_db()


@router.get("/", response_model=ServiceStatusResponse)
async def service_status():
    """Check the status and health of service."""
    return ServiceStatusResponse(version=__version__, status="healthy")


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
    "/sharing",
    dependencies=[
        Depends(authenticate),
        Depends(require_read_write_permissions),
        Depends(authorize),
    ],
    response_model=SharedFileResponseModel,
)
async def patch_file(body: SharedFileRequestModel) -> SharedFileResponseModel:
    storage_manager: BaseStorageManager = router.app.storage_manager
    return await storage_manager.update(body)


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
