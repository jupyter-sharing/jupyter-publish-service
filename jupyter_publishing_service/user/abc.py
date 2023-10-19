from abc import ABC, abstractmethod
from jupyter_publishing_service.models import UserOrGroup

class UserStore(ABC):
    @abstractmethod
    def search_users(self, search_string: str) -> List[UserOrGroup]:
        """
        Search for user name

        This must be non-blocking co-routine

        Must return username on successful authentication,
        and return None on failed authentication

        Args:
            search_string (dict): Login data

        Returns:
            users (List[UserOrGroup]): Must return a list of users
        """
        ...


    @abstractmethod
    def search_groups(self, search_string: str) -> List[UserOrGroup]:
        """
        Search for groups from user store
        """
        ...