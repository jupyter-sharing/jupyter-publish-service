from abc import ABCMeta, abstractmethod

from jupyter_publishing_service.models.sql import User


class AuthenticatorABC(metaclass=ABCMeta):
    @abstractmethod
    async def authenticate(self, token: str) -> User:
        """
        Authenticate a user with login data

        This must be non-blocking co-routine

        Must return username on successful authentication,
        and return None on failed authentication

        Args:
            data (dict): Login data

        Returns:
            user (dict or None): Must return a dict with key 'name' with a unique value. Can include other fields
        """
        raise NotImplementedError
