"""JupyterHub authenticator.

Validates an incoming bearer token by asking the Hub to identify the
caller (`GET /hub/api/user`), and checks that the caller holds the
required scope before admitting them.

Tokens issued by JupyterHub are opaque strings (not JWTs), so the Hub
is the only authority that can validate them; this module deliberately
does not attempt local signature verification.

Design notes
------------
* Tokens are cached for `cache_max_age` seconds keyed by token, mirroring
  the cache `jupyterhub.services.auth.HubAuth` keeps. One Hub roundtrip
  per (authority, token) per `cache_max_age` window.
* Scope checking uses `jupyterhub.services.auth.check_scopes`, which
  correctly handles filter syntax like `read:users!group=class-a` where
  a naive `in` test would silently fail.
* Configuration falls back to `$JUPYTERHUB_API_URL` so a managed-service
  deployment works out of the box; explicit `hub_api_url` config wins
  when set.
"""
import os
import time
from typing import Optional, Set

from fastapi import HTTPException
from httpx import AsyncClient
from jupyterhub.services.auth import check_scopes
from traitlets import Int, Set as TraitSet, Unicode
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.authenticator.abc import AuthenticatorABC
from jupyter_publishing_service.models.sql import User


class HubAuthenticator(LoggingConfigurable):

    authority = Unicode(
        config=True,
        help="The authority value stamped onto every authenticated User. "
        "Normally inherited from JupyterPublishingService.authority.",
    )

    hub_api_url = Unicode(
        config=True,
        help=(
            "Base URL for the Hub REST API, e.g. http://hub:8081/hub/api. "
            f"Falls back to ${constants.JUPYTERHUB_API_URL}."
        ),
    )

    required_scopes = TraitSet(
        Unicode(),
        default_value={constants.JUPYTERHUB_SCOPE},
        config=True,
        help="Scopes the caller must hold to use the publishing service. "
        "Filter syntax (e.g. `read:users!group=class-a`) is honoured via "
        "jupyterhub.services.auth.check_scopes.",
    )

    cache_max_age = Int(
        default_value=300,
        config=True,
        help="Seconds to cache /hub/api/user responses per token.",
    )

    verify_ssl = Unicode(
        default_value="",
        config=True,
        help="Path to a CA bundle for HTTPS verification, or empty string for "
        "the system default. Set to '0' to disable verification (NOT for prod).",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.hub_api_url:
            self.hub_api_url = os.environ.get(constants.JUPYTERHUB_API_URL, "")
        if not self.hub_api_url:
            raise ValueError(
                "HubAuthenticator.hub_api_url is not set and "
                f"${constants.JUPYTERHUB_API_URL} is not in the environment."
            )
        self.hub_api_url = self.hub_api_url.rstrip("/")
        # token -> (User, expires_at_unix)
        self._token_cache: dict[str, tuple[User, float]] = {}

    def _verify_arg(self):
        if self.verify_ssl == "":
            return True
        if self.verify_ssl == "0":
            return False
        return self.verify_ssl

    def _cached(self, token: str) -> Optional[User]:
        entry = self._token_cache.get(token)
        if entry is None:
            return None
        user, expires_at = entry
        if expires_at < time.monotonic():
            self._token_cache.pop(token, None)
            return None
        return user

    def _cache(self, token: str, user: User) -> None:
        self._token_cache[token] = (user, time.monotonic() + self.cache_max_age)

    async def authenticate(self, token: str) -> Optional[User]:
        cached = self._cached(token)
        if cached is not None:
            return cached

        async with AsyncClient(verify=self._verify_arg()) as client:
            r = await client.get(
                f"{self.hub_api_url}/user",
                headers={"Authorization": f"token {token}"},
            )

        if r.status_code == 401:
            # Hub does not recognise this token at all.
            return None
        if r.status_code == 403:
            raise HTTPException(status_code=403, detail="Hub rejected token")
        if r.status_code != 200:
            self.log.warning(
                "Unexpected Hub response while validating token: status=%s body=%s",
                r.status_code,
                r.text[:200],
            )
            raise HTTPException(status_code=502, detail="Hub auth failed")

        model = r.json()
        scopes: Set[str] = set(model.get("scopes", []))
        if not check_scopes(self.required_scopes, scopes):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Caller missing required scope(s): "
                    f"{sorted(self.required_scopes)}"
                ),
            )

        username = model.get("name")
        if not username:
            self.log.error("Hub /user response missing 'name': %s", model)
            raise HTTPException(status_code=502, detail="Malformed Hub response")

        user = User(authority=self.authority, username=username)
        self._cache(token, user)
        return user


AuthenticatorABC.register(HubAuthenticator)
