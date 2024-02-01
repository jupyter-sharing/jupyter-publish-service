from fastapi import APIRouter, Depends
from jupyter_server.utils import ensure_async
from sqlmodel import select

from .models import Collaborator, CreateSharedFile, SharedFile

router = APIRouter()


@router.on_event("startup")
async def on_startup():
    app = router.app
    session_manager = app.session_manager
    await session_manager.create_db()


# @router.get("/sharing/{file_id}", response_model=SharedFile)
# async def get_file(file_id: str):
#     app = router.app
#     cm = app.file_manager
#
#     file = await ensure_async(cm.get())
#     return SharedFile()


@router.get("/sharing/{file_id}/collaborators", response_model=list[Collaborator])
async def get_collaborators(file_id: str):
    app = router.app
    store = app.collaborator_store
    f = SharedFile(id=file_id)
    return await store.get(f)


# @router.post("/sharing/{file_id}/collaborators", response_model=list[Collaborator])
# async def add_collaborators(file_id: str, collaborators: list[Collaborator]):
#     app = router.app
#     store = app.collaborator_store
#
#     return collaborator


@router.post("/sharing", response_model=SharedFile)
async def add_file(body: CreateSharedFile) -> SharedFile:
    app = router.app
    store = app.collaborator_store
    collaborators = body.collaborators
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
    return shared_file
    # Save to content store
