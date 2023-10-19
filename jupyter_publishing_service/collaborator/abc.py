from abc import ABC, abstractmethod
from jupyter_publishing_service.models import UserOrGroup
class CollaboratorStore(ABC):

    @abstractmethod
    def add(self, user: UserOrGroup, file: SharedFile, permissions: list[str]) -> bool:
        """
        Add the user as a collaborator on the given file with given permissions
        """
        ...


    @abstractmethod
    def delete(self, user: UserOrGroup, file: SharedFile) -> bool:
        """
        Remove the user as a collaborator on the give file
        """
        ...


    @abstractmethod
    def update(self, user: UserOrGroup, file: SharedFile, permissions: list[str]) -> bool:
        """
        Update user's permissions on the given file
        User must be a collaborotor on the file
        """
        ...


