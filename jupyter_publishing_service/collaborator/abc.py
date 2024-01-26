from abc import ABC, abstractmethod
from jupyter_publishing_service.models import Collaborator, SharedFile, CollaboratorRole, Role


class CollaboratorStore(ABC):

    @abstractmethod
    async def add(self, user: Collaborator, file: SharedFile, roles: list[Role]):
        """
        Add the user as a collaborator on the given file with given roles
        """
        ...

    @abstractmethod
    async def delete(self, user: Collaborator, file: SharedFile):
        """
        Remove the user as a collaborator on the give file
        """
        ...

    @abstractmethod
    async def update(self, user: Collaborator, file: SharedFile, roles: list[Role]):
        """
        Update user's permissions on the given file
        User must be a collaborotor on the file
        """
        ...

    @abstractmethod
    async def get(self, file: SharedFile) -> list[CollaboratorRole]:
        """
        Get collaborators on a given file with their permissions
        """
        ...
