import uuid
from abc import ABCMeta, abstractmethod
from typing import List

from jupyter_publishing_service.models.sql import SharedFileMetadata


class MetadataStoreABC(metaclass=ABCMeta):
    @abstractmethod
    async def add(self, metadata: SharedFileMetadata) -> SharedFileMetadata:
        """
        Add a user as a collaborator on the given file with given roles
        """
        return NotImplemented

    @abstractmethod
    async def delete(self, file_id: str):
        """
        Remove the user as a collaborator on the give file
        """
        return NotImplemented

    @abstractmethod
    async def update(self, metadata: SharedFileMetadata) -> SharedFileMetadata:
        """
        Update user's permissions on the given file
        User must be a collaborator on the file
        """
        return NotImplemented

    @abstractmethod
    async def get(self, file_id: str) -> SharedFileMetadata:
        """
        Get collaborators on a given file with their permissions
        """
        return NotImplemented

    @abstractmethod
    async def list(self, list_of_file_ids: List[str]) -> List[SharedFileMetadata]:
        return NotImplemented
