from abc import ABC, abstractmethod
from typing import List

from jupyter_publishing_service.models.sql import Collaborator


class UserStoreABC(ABC):
    @abstractmethod
    async def search_users(self, search_string: str) -> List[Collaborator]:
        """
        Search for users

        This must be non-blocking co-routine

        Must return list of users

        Args:
            search_string (dict): partial name or email address

        Returns:
            users (List[Collaborator]): Must return a list of users
        """
        return NotImplemented

    @abstractmethod
    async def search_groups(self, search_string: str) -> List[Collaborator]:
        """
        Search for groups

        This must be non-blocking co-routine

        Must return list of groups

        Args:
            search_string (dict): partial name or email address

        Returns:
        """

        return NotImplemented
