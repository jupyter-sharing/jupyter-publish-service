from abc import ABC, abstractmethod
from typing import List, Optional

from jupyter_publishing_service.models.rest import (
    ServiceStatusResponse,
    SharedFileRequestModel,
    SharedFileResponseModel,
)
from jupyter_publishing_service.models.sql import User


class ClientABC(ABC):
    @abstractmethod
    async def service_status(self) -> ServiceStatusResponse:
        ...

    @abstractmethod
    async def list_files(self) -> List[SharedFileResponseModel]:
        ...

    @abstractmethod
    async def get_file(
        self, file_id: str, contents: bool = False, collaborators: bool = False
    ) -> SharedFileResponseModel:
        ...

    @abstractmethod
    async def add_file(self, request: SharedFileRequestModel) -> SharedFileResponseModel:
        ...

    @abstractmethod
    async def update_file(self, request: SharedFileRequestModel) -> SharedFileResponseModel:
        ...

    @abstractmethod
    async def delete_file(self, file_id: str):
        ...

    @abstractmethod
    async def search_users(substring: Optional[str] = None) -> List[User]:
        ...
