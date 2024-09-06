from abc import ABC, abstractmethod

from ..models.rest import SharedFileRequestModel, SharedFileResponseModel
from ..models.sql import Collaborator


class StorageManagerABC(ABC):
    """A manager in charge of storing and gathering
    data about a shared file. The data for any single file
    could be stored in various local/remote locations. The
    job of the storage manager is to know where to find this data
    and optimize queries/requests based on these sources.
    """

    @abstractmethod
    def initialize(self):
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def start(
        self,
        user,
    ):
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def authorize(self, user: Collaborator, file_id: str):
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def get(
        self, file_id: str, collaborators: bool = False, contents: bool = False
    ) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def add(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def delete(self, file_id: str):
        raise NotImplementedError("Must be implemented in a subclass.")

    @abstractmethod
    async def update(self, request_model: SharedFileRequestModel) -> SharedFileResponseModel:
        raise NotImplementedError("Must be implemented in a subclass.")
