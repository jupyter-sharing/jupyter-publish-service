import uuid
from abc import ABCMeta, abstractmethod
from typing import List

from jupyter_publishing_service.models import (
    Collaborator,
    CollaboratorRole,
    Role,
    SharedFile,
    SharedFileWithCollaborators,
)


class CollaboratorStore(metaclass=ABCMeta):
    @abstractmethod
    async def add(self, collaborator: Collaborator, file: SharedFile, roles: List[Role]):
        """
        Add a user as a collaborator on the given file with given roles
        """
        return NotImplemented

    @abstractmethod
    async def delete(self, collaborator: Collaborator, file: SharedFile):
        """
        Remove the user as a collaborator on the give file
        """
        return NotImplemented

    @abstractmethod
    async def update(self, collaborator: Collaborator, file: SharedFile, roles: List[Role]):
        """
        Update user's permissions on the given file
        User must be a collaborator on the file
        """
        return NotImplemented

    @abstractmethod
    async def get(self, file: uuid.UUID) -> SharedFileWithCollaborators:
        """
        Get collaborators on a given file with their permissions
        """
        return NotImplemented
