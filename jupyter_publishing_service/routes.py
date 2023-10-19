from fastapi import APIRouter
from jupyter_server.utils import ensure_async

from .models import SharedFile

router = APIRouter()

@router.get("/sharing/{file_id}", response_model=SharedFile)
async def get_file(file_id):
    app = router.app
    cm = app.file_manager

    file = await ensure_async(cm.get())
    return SharedFile()
