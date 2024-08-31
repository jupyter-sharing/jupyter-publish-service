from typing import List

from traitlets import Instance, Type
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.collaborator.abc import CollaboratorStoreABC
from jupyter_publishing_service.collaborator.sql import SQLCollaboratorStore
from jupyter_publishing_service.file.abc import FileStoreABC
from jupyter_publishing_service.file.sql import SQLFileStore
from jupyter_publishing_service.metadata.abc import MetadataStoreABC
from jupyter_publishing_service.metadata.sql import SQLMetadataStore
from jupyter_publishing_service.user.abc import UserStoreABC
from jupyter_publishing_service.user.sql import SQLUserStore

from .models.rest import SharedFileRequestModel, SharedFileResponseModel
from .models.sql import (
    Collaborator,
    CollaboratorRole,
    JupyterContentsModel,
    Role,
    SharedFileMetadata,
)


class BaseStorageManager(LoggingConfigurable):
    """A manager in charge of storing and gathering
    data about a shared file. The data for any single file
    could be stored in various local/remote locations. The
    job of the storage manager is to know where to find this data
    and optimize queries/requests based on these sources.
    """

    metadata_store_class = Type(
        default_value=SQLMetadataStore,
        klass="jupyter_publishing_service.metadata.abc.MetadataStoreABC",
    ).tag(config=True)

    collaborator_store_class = Type(
        default_value=SQLCollaboratorStore,
        klass="jupyter_publishing_service.collaborator.abc.CollaboratorStoreABC",
    ).tag(config=True)

    file_store_class = Type(
        default_value=SQLFileStore,
        klass="jupyter_publishing_service.file.abc.FileStoreABC",
    ).tag(config=True)

    user_store_class = Type(
        default_value=SQLUserStore,
        klass="jupyter_publishing_service.user.abc.UserStoreABC",
    ).tag(config=True)

    metadata_store: MetadataStoreABC = Instance(
        klass="jupyter_publishing_service.metadata.abc.MetadataStoreABC",
        allow_none=True,
    )

    collaborator_store: CollaboratorStoreABC = Instance(
        klass="jupyter_publishing_service.collaborator.abc.CollaboratorStoreABC",
        allow_none=True,
    )

    file_store: FileStoreABC = Instance(
        klass="jupyter_publishing_service.file.abc.FileStoreABC",
        allow_none=True,
    )

    user_store: UserStoreABC = Instance(
        klass="jupyter_publishing_service.user.abc.UserStoreABC",
        allow_none=True,
    )

    def initialize(self):
        raise NotImplementedError("Must be implemented in a subclass.")

    async def get(
        self, file_id: str, collaborators: bool = False, contents: bool = False
    ) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")

    async def add(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")

    async def delete(self, file_id: str):
        raise NotImplementedError("Must be implemented in a subclass.")

    async def update(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")


class SQLStorageManager(BaseStorageManager):
    def initialize(self):
        self.metadata_store = self.metadata_store_class(parent=self, log=self.log)
        self.collaborator_store = self.collaborator_store_class(parent=self, log=self.log)
        self.file_store = self.file_store_class(parent=self, log=self.log)
        self.user_store = self.user_store_class(parent=self, log=self.log)

    async def get(
        self, file_id: str, collaborators: bool = False, contents: bool = False
    ) -> SharedFileResponseModel:
        metadata: SharedFileMetadata = await self.metadata_store.get(file_id)
        collaborator_roles = None
        if collaborators:
            collaborator_roles: List[CollaboratorRole] = await self.collaborator_store.get(file_id)
        file = None
        if contents:
            file: JupyterContentsModel = await self.file_store.get(file_id=file_id)
        return SharedFileResponseModel(
            metadata=metadata, collaborator_roles=collaborator_roles, contents=file
        )

    async def add(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        """
        Store a new shared file.

        Returns a SharedFileResponse without contents and collaborators.
        """
        metadata = await self.metadata_store.add(request_model.metadata)
        if request_model.collaborators:
            for collaborator in request_model.collaborators:
                # The author should have writer permissions.
                if collaborator.email == metadata.author:
                    await self.collaborator_store.add(
                        request_model.metadata.id, collaborator, [Role(name="WRITER")]
                    )
                    continue
                await self.collaborator_store.add(
                    request_model.metadata.id, collaborator, request_model.roles
                )
        if request_model.contents:
            await self.file_store.add(metadata.id, request_model.contents)
        return SharedFileResponseModel(metadata=metadata)

    async def delete(self, file_id: str):
        # Need to remove collaborators for this file.
        collaborator_roles = await self.collaborator_store.get(file_id=file_id)
        # NOTE: we should refactor this to delete as a batch, not one-by-one.
        for cr in collaborator_roles:
            await self.collaborator_store.delete(file_id, Collaborator(email=cr.email))
        # Delete file and metadata
        await self.file_store.delete(file_id)
        await self.metadata_store.delete(file_id)

    async def update(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        metadata = await self.metadata_store.update(request_model.metadata)
        if request_model.collaborators:
            await self.collaborator_store.update(
                request_model.metadata.id, request_model.collaborators, request_model.roles
            )
        if request_model.contents:
            await self.file_store.add(metadata.id, request_model.contents)
        return SharedFileResponseModel(metadata=metadata)
