"""User store backed by JupyterHub's /hub/api/users endpoint.

Used when the publishing service is fronting one or more JupyterHubs.
The autocomplete in JupyterLab's sharing dialog calls
`GET /sharing/users?substring=...`; with the share-DB-only-after-creation
rule, the publishing service's own `User` table does not contain users
who have never been in a share yet, so the autocomplete needs an
external source.

Token used for /hub/api/users
-----------------------------
This store uses the **service's own** Hub API token (env
`$JUPYTERHUB_API_TOKEN`), not the request token. The service must be
granted `list:users` in `c.JupyterHub.load_roles` (with
`services: ["<this service name>"]`).

Note: an alternative model uses the request token here so results
inherit the caller's hub-level permissions, in exchange for granting
`list:users` to every user. Operators who want that tradeoff can plug
in a different user-store implementation.
"""
import os
from typing import List, Optional

from httpx import AsyncClient
from traitlets import Int, Unicode
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.models.sql import User
from jupyter_publishing_service.user.abc import UserStoreABC


class HubUserStore(LoggingConfigurable):

    authority = Unicode(
        config=True,
        help="Authority stamped onto User rows returned by this store. "
        "Normally inherited from JupyterPublishingService.authority.",
    )

    hub_api_url = Unicode(
        config=True,
        help="Base URL for the Hub REST API (e.g. http://hub:8081/hub/api). "
        f"Falls back to ${constants.JUPYTERHUB_API_URL}.",
    )

    service_api_token = Unicode(
        config=True,
        help="Hub API token belonging to the publishing service itself. "
        "Must be granted `list:users` via c.JupyterHub.load_roles. "
        f"Falls back to ${constants.JUPYTERHUB_API_TOKEN}.",
    )

    page_size = Int(
        default_value=200,
        config=True,
        help="Page size for /hub/api/users pagination.",
    )

    verify_ssl = Unicode(default_value="", config=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.hub_api_url:
            self.hub_api_url = os.environ.get(constants.JUPYTERHUB_API_URL, "")
        if not self.service_api_token:
            self.service_api_token = os.environ.get(constants.JUPYTERHUB_API_TOKEN, "")
        if not self.hub_api_url:
            raise ValueError(
                "HubUserStore.hub_api_url is not set and "
                f"${constants.JUPYTERHUB_API_URL} is not in the environment."
            )
        if not self.service_api_token:
            raise ValueError(
                "HubUserStore.service_api_token is not set and "
                f"${constants.JUPYTERHUB_API_TOKEN} is not in the environment."
            )
        self.hub_api_url = self.hub_api_url.rstrip("/")

    def _verify_arg(self):
        if self.verify_ssl == "":
            return True
        if self.verify_ssl == "0":
            return False
        return self.verify_ssl

    async def search_users(self, search_string: Optional[str]) -> List[User]:
        headers = {"Authorization": f"token {self.service_api_token}"}
        users: List[User] = []
        offset = 0
        async with AsyncClient(verify=self._verify_arg()) as client:
            while True:
                params: dict = {"limit": self.page_size, "offset": offset}
                if search_string:
                    params["name_filter"] = search_string
                r = await client.get(
                    f"{self.hub_api_url}/users",
                    headers=headers,
                    params=params,
                )
                if r.status_code == 403:
                    self.log.warning(
                        "Hub returned 403 for /users; the service token is "
                        "missing the `list:users` scope. Returning empty list."
                    )
                    return users
                r.raise_for_status()
                page = r.json() or []
                users.extend(
                    User(authority=self.authority, username=u["name"]) for u in page
                )
                if len(page) < self.page_size:
                    break
                offset += self.page_size
        return users

    async def search_groups(self, search_string: Optional[str] = None) -> List[User]:
        # Group search not yet implemented; return empty list.
        return []


UserStoreABC.register(HubUserStore)
