from abc import ABCMeta, abstractmethod
from typing import List

from jupyter_publishing_service.models.sql import Collaborator, Role, User


class CollaboratorStoreABC(metaclass=ABCMeta):
    @abstractmethod
    async def get(self, file_id: str) -> List[Collaborator]:
        """
        Get collaborators on a given file with their permissions
        """
        return NotImplemented

    @abstractmethod
    async def add(self, file_id: str, collaborator: User, roles: List[Role]):
        """
        Add a user as a collaborator on the given file with given roles
        """
        return NotImplemented

    @abstractmethod
    async def delete(self, file_id: str, collaborator: User):
        """
        Remove the user as a collaborator on the give file
        """
        return NotImplemented

    @abstractmethod
    async def update(self, file_id: str, collaborator: User, roles: List[Role]):
        """
        Update user's permissions on the given file
        User must be a collaborator on the file
        """
        return NotImplemented

    @abstractmethod
    async def list(self, user_id: str) -> List[str]:
        """
        Update user's permissions on the given file
        User must be a collaborator on the file
        """
        return NotImplemented
