import uuid
from typing import List

from fastapi import APIRouter, Depends, Request
from pydantic_core import from_json

from .authenticator.service import authenticate
from .authorizer.service import (
    authorize,
    require_read_permissions,
    require_read_write_permissions,
)
from .database.manager import create_db
from .models import (
    CollaboratorRole,
    CreateSharedFile,
    PatchSharedFile,
    SharedFile,
    SharedFileWithCollaborators,
)

router = APIRouter()


@router.on_event("startup")
async def on_startup():
    await create_db()


@router.get(
    "/sharing/{file_id}/collaborators",
    dependencies=[Depends(authenticate), Depends(require_read_permissions), Depends(authorize)],
    response_model=List[CollaboratorRole],
)
async def get_collaborators(file_id: uuid.UUID, request: Request) -> List[CollaboratorRole]:
    app = router.app
    print(request.state.user)
    store = app.collaborator_store
    results = await store.get(file=file_id)
    return results.collaborators


@router.get(
    "/sharing/{file_id}",
    dependencies=[Depends(authenticate), Depends(require_read_permissions), Depends(authorize)],
    response_model=SharedFileWithCollaborators,
)
async def get_file(
    file_id: uuid.UUID, content: bool, request: Request
) -> SharedFileWithCollaborators:
    app = router.app
    print(request.state.user)
    store = app.collaborator_store
    file_manager = app.file_manager
    results = await store.get(file=file_id)
    if content:
        c = await file_manager.get(path=file_id, content=True, type="notebook")
        results.content = c
    return results


@router.post("/sharing", response_model=SharedFile)
async def add_file(body: CreateSharedFile) -> SharedFile:
    app = router.app
    store = app.collaborator_store
    collaborators = body.collaborators
    file_manager = app.file_manager
    roles = body.roles
    shared_file = SharedFile(
        id=body.id,
        name=body.name,
        title=body.title,
        author=body.author,
        version=1,
        shareable_link="http://127.0.0.1:9000/" + f"{body.id}",
    )
    for collaborator in collaborators:
        await store.add(collaborator=collaborator, file=shared_file, roles=roles)
    await file_manager.save(body.contents, body.id)
    return shared_file


@router.patch(
    "/sharing/{file_id}",
    dependencies=[
        Depends(authenticate),
        Depends(require_read_write_permissions),
        Depends(authorize),
    ],
    response_model=SharedFileWithCollaborators,
)
async def patch_file(file_id: str, body: PatchSharedFile) -> SharedFileWithCollaborators:
    app = router.app
    store = app.collaborator_store
    current = await store.get(file=file_id)
    shared_file = SharedFile(
        id=current.file.id,
        name=current.file.name if body.name is None else body.name,
        title=current.file.title if body.title is None else body.title,
        author=current.file.author,
        version=current.file.version + 1,  # Only if jupyterContents model changes
        shareable_link=current.file.shareable_link,
    )
    collaborators = current.file.collaborators if body.collaborators is None else body.collaborators
    roles = body.roles  # If empty, no update to roles for any collaborator
    for collaborator in collaborators:
        await store.update(collaborator=collaborator, file=shared_file, roles=roles)
    return await store.get(file_id)
