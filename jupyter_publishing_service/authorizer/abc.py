from abc import ABC, abstractmethod

class Authorizer(ABC):
    @abstractmethod
    def authorize(self, user, data) -> dict:
        """
        Authorizer a user with given data

        This must be non-blocking co-routine

        Must return True if user is authorized, False if not

        Args:
            user (dict): user dict with key 'name'
            data (dict): data dict that helps making authorization decision
                        Will contain atleast 'path' and 'method'

        Returns:
            boolean (True or False): Must return whether user is authorized to perform requested action on path
        """
        ...