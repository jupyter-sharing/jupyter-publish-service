from httpx import AsyncClient
from traitlets import Unicode
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.constants import JUPYTERHUB_SCOPE
from jupyter_publishing_service.models.sql import User

from .abc import AuthenticatorABC


class HubAuthenticator(LoggingConfigurable):

    hub_url = Unicode(default_value="http://localhost:8000").tag(config=True)

    async def authenticate(self, token: str) -> User:
        user_endpoint = self.hub_url + "/hub/api/user"
        auth_header = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(verify=False) as client:
            r = await client.get(user_endpoint, headers=auth_header)
            user_model = r.json()
            user_scopes = user_model["scopes"]
            assert JUPYTERHUB_SCOPE in user_scopes
            return User(username=user_model.get("username"))


AuthenticatorABC.register(HubAuthenticator)
