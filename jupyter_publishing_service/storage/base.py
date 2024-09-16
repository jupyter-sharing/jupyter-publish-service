from typing import List, Optional

from traitlets import Instance, Type, default
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.authorizer.sqlrbac import SQLRoleBasedAuthorizer
from jupyter_publishing_service.collaborator.abc import CollaboratorStoreABC
from jupyter_publishing_service.collaborator.sql import SQLCollaboratorStore
from jupyter_publishing_service.file.abc import FileStoreABC
from jupyter_publishing_service.file.sql import SQLFileStore
from jupyter_publishing_service.metadata.abc import MetadataStoreABC
from jupyter_publishing_service.metadata.sql import SQLMetadataStore
from jupyter_publishing_service.user.abc import UserStoreABC
from jupyter_publishing_service.user.sql import SQLUserStore

from ..models.rest import SharedFileRequestModel, SharedFileResponseModel
from ..models.sql import (
    Collaborator,
    CollaboratorRole,
    JupyterContentsModel,
    Role,
    SharedFileMetadata,
)
from .abc import StorageManagerABC


class BaseStorageManager(LoggingConfigurable):

    authorization_store_class = Type(kclass=AuthorizerABC).tag(config=True)

    @default("authorization_store_class")
    def _default_authorization_store_class(self):
        return SQLRoleBasedAuthorizer

    metadata_store_class = Type(klass=MetadataStoreABC).tag(config=True)

    @default("metadata_store_class")
    def _default_metadata_store_class(self):
        return SQLMetadataStore

    collaborator_store_class = Type(klass=CollaboratorStoreABC).tag(config=True)

    @default("collaborator_store_class")
    def _default_collaborator_store_class(self):
        return SQLCollaboratorStore

    file_store_class = Type(klass=FileStoreABC).tag(config=True)

    @default("file_store_class")
    def _default_file_store_class(self):
        return SQLFileStore

    user_store_class = Type(klass=UserStoreABC).tag(config=True)

    @default("user_store_class")
    def _default_user_store_class(self):
        return SQLUserStore

    authorization_store: AuthorizerABC = Instance(
        klass="jupyter_publishing_service.authorizer.abc.AuthorizerABC",
        allow_none=True,
    )

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
        self.authorization_store = self.authorization_store_class(parent=self, log=self.log)
        self.metadata_store = self.metadata_store_class(parent=self, log=self.log)
        self.collaborator_store = self.collaborator_store_class(parent=self, log=self.log)
        self.file_store = self.file_store_class(parent=self, log=self.log)
        self.user_store = self.user_store_class(parent=self, log=self.log)

    async def start(self):
        # Don't do anything here. Subclasses can use this to initialize a e.g. database.
        ...

    async def authorize(self, user: Collaborator, file_id: str) -> bool:
        return await self.authorization_store.authorize(user, file_id)

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
                if collaborator.name == metadata.author:
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
            await self.collaborator_store.delete(file_id, Collaborator(name=cr.name))
        # Delete file and metadata
        await self.file_store.delete(file_id)
        await self.metadata_store.delete(file_id)

    async def update(
        self, file_id: str, request_model: SharedFileRequestModel
    ) -> SharedFileResponseModel:
        metadata = await self.metadata_store.update(request_model.metadata)
        if request_model.collaborators:
            await self.collaborator_store.update(
                file_id, request_model.collaborators, request_model.roles
            )
        if request_model.contents:
            await self.file_store.add(file_id, request_model.contents)
        return SharedFileResponseModel(metadata=metadata)

    async def list(self, user_id: str) -> List[SharedFileResponseModel]:
        file_ids = await self.collaborator_store.list(user_id)
        metadatas = await self.metadata_store.list(file_ids)
        return [SharedFileResponseModel(metadata=m) for m in metadatas]

    async def search_users(self, substring: Optional[str]) -> List[Collaborator]:
        return await self.user_store.search_users(substring)


StorageManagerABC.register(BaseStorageManager)
