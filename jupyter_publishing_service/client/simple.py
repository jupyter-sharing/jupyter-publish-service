from typing import List, Optional

from httpx import AsyncClient, RequestError
from traitlets import Unicode
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.rest import (
    ServiceStatusResponse,
    SharedFileRequestModel,
    SharedFileResponseModel,
)
from jupyter_publishing_service.models.sql import User

from .abc import ClientABC


def check_token(method):
    async def _inner(self: "AsyncPublishingClient", *args, **kwargs):
        if not self.token_is_valid():
            self.api_token = await self.fetch_token()
        return await method(self, *args, **kwargs)

    return _inner


class AsyncPublishingClient(LoggingConfigurable):
    """Simple Publishing Service Client."""

    service_url = Unicode(default_value="http://localhost:9000").tag(config=True)
    api_token = Unicode(allow_none=True).tag(config=True)
    key_id = Unicode(allow_none=True).tag(config=True)

    @property
    def headers(self) -> dict:
        if self.api_token:
            headers = {"Authorization": f"Bearer {self.api_token}"}
            if self.key_id:
                headers["kid"] = self.key_id
            return headers
        return {}

    def token_is_valid(self) -> bool:
        if self.api_token is None:
            return False
        return True

    async def fetch_token(self) -> str:
        if self.api_token is None:
            raise RequestError("No valid token.")

    async def service_status(self) -> ServiceStatusResponse:
        url = self.service_url + "/"
        async with AsyncClient(verify=True) as client:
            response = await client.get(url)
            return ServiceStatusResponse.model_validate(response.json())

    @check_token
    async def list_files(self) -> List[SharedFileResponseModel]:
        url = self.service_url + "/sharing"
        async with AsyncClient(verify=True) as client:
            response = await client.get(url, headers=self.headers)
            data = response.json()
            return [SharedFileResponseModel.model_validate(item) for item in data]

    @check_token
    async def get_file(
        self, file_id: str, contents: bool = False, collaborators: bool = False
    ) -> SharedFileResponseModel:
        url = (
            self.service_url
            + f"/sharing/{file_id}?contents={int(contents)}&collaborators={int(collaborators)}"
        )
        async with AsyncClient(verify=True) as client:
            response = await client.get(url, headers=self.headers)
            return SharedFileResponseModel.model_validate(response.json())

    @check_token
    async def add_file(self, request: SharedFileRequestModel) -> SharedFileResponseModel:
        url = self.service_url + f"/sharing"
        async with AsyncClient(verify=True) as client:
            response = await client.post(url, headers=self.headers, json=request.model_dump())
            if response.is_client_error:
                raise Exception()
            return SharedFileResponseModel.model_validate(response.json())

    @check_token
    async def update_file(self, request: SharedFileRequestModel) -> SharedFileResponseModel:
        url = self.service_url + f"/sharing/{request.metadata.id}"
        async with AsyncClient(verify=True) as client:
            response = await client.post(url, headers=self.headers, json=request.model_dump_json())
            return SharedFileResponseModel.model_validate(response.json())

    @check_token
    async def delete_file(self, file_id: str):
        url = self.service_url + f"/sharing/{file_id}"
        async with AsyncClient(verify=True) as client:
            await client.delete(url, headers=self.headers)

    @check_token
    async def search_users(self, substring: Optional[str] = None) -> List[User]:
        url = self.service_url + "/sharing/users"
        if substring:
            url += "?substring={substring}"
        async with AsyncClient(verify=True) as client:
            response = await client.get(url, headers=self.headers)
            collaborators = []
            for item in response.json():
                collab = User.model_validate(item)
                collaborators.append(collab)
            return collaborators


ClientABC.register(AsyncPublishingClient)
