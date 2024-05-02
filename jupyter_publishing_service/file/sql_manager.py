import uuid

from jupyter_server.services.contents.filemanager import AsyncFileContentsManager
from sqlmodel import select

from jupyter_publishing_service.database.manager import get_session
from jupyter_publishing_service.file.helper import create_or_update_jupyter_contents
from jupyter_publishing_service.models import JupyterContentsModel


class SQLManager(AsyncFileContentsManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = get_session

    async def get(self, path, content=True, type=None, format=None) -> dict:
        """Takes a path for an entity and returns its model

        Parameters
        ----------
        path : str
            the API path that describes the relative path for the target
        content : bool
            Whether to include the contents in the reply
        type : str, optional
            The requested type - 'file', 'notebook', or 'directory'.
            Will raise HTTPError 400 if the content doesn't match.
        format : str, optional
            The requested format for file contents. 'text' or 'base64'.
            Ignored if this returns a notebook or directory model.

        Returns
        -------
        model : dict
            the contents model. If content=True, returns the contents
            of the file or directory as well.
        """
        if type != "notebook":
            return {}
        path_uuid = uuid.UUID(path)
        async with self._session() as session:
            stmt = select(JupyterContentsModel).where(JupyterContentsModel.id == path_uuid)
            results = await session.exec(stmt)
            nb = results.first()
            return nb.model_dump(mode="json")

    async def save(self, model, path="") -> dict:
        """Save the file model and return the model with no content."""
        path_uuid = uuid.UUID(path) if path is not None else None
        async with self._session() as session:
            jcm = JupyterContentsModel.model_validate(model)
            jcm.id = path_uuid if path_uuid is not None else jcm.id
            await create_or_update_jupyter_contents(session, jcm)
            jcm.content = None
            return jcm.model_dump(exclude_unset=True, mode="json")

    async def delete_file(self, path):
        """Delete file at path."""
        async with self._session() as session:
            statement = select(JupyterContentsModel.id).where(JupyterContentsModel.id == path)
            results = await session.exec(statement)
            for result in results:
                session.delete(result)
            await session.commit()
