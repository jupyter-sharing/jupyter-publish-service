from abc import ABC, abstractmethod
from typing import List

from jupyter_publishing_service.models.sql import User


class UserStoreABC(ABC):
    @abstractmethod
    async def search_users(self, search_string: str) -> List[User]:
        """
        Search for users

        This must be non-blocking co-routine

        Must return list of users

        Args:
            search_string (dict): partial name or email address

        Returns:
            users (List[User]): Must return a list of users
        """
        return NotImplemented

    @abstractmethod
    async def search_groups(self, search_string: str) -> List[User]:
        """
        Search for groups

        This must be non-blocking co-routine

        Must return list of groups

        Args:
            search_string (dict): partial name or email address

        Returns:
        """

        return NotImplemented
