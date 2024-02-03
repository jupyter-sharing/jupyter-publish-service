from abc import ABC, abstractmethod


class AuthorizerABC(ABC):
    @abstractmethod
    def authorize(self, user, data) -> bool:
        """
        Authorizer a user with given data

        This must be non-blocking co-routine

        Must return True if user is authorized, False if not

        Args:
            user (dict): user dict with key 'name'
            data (dict): dict representation of the resource being considered.
            Contains a key called permissions to indicate the required list of permissions

        Returns:
            boolean (True or False): Must return whether user is authorized to perform requested action on path
        """
        return NotImplemented
