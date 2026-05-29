"""Tests for the JupyterHub-backed authenticator."""
import os

import httpx
import pytest
import respx
from fastapi import HTTPException

from jupyter_publishing_service.authenticator.hub import HubAuthenticator

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


HUB_API = "http://hub.test/hub/api"
AUTHORITY = "hub.test"


def _auth(**overrides) -> HubAuthenticator:
    kwargs = {
        "authority": AUTHORITY,
        "hub_api_url": HUB_API,
    }
    kwargs.update(overrides)
    return HubAuthenticator(**kwargs)


async def test_authenticate_returns_user_with_required_scope():
    auth = _auth()
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(
            return_value=httpx.Response(
                200,
                json={"name": "alice", "scopes": ["custom:publishing"]},
            )
        )
        user = await auth.authenticate("alice-token")
    assert user is not None
    assert user.username == "alice"
    assert user.authority == AUTHORITY


async def test_authenticate_returns_none_on_401_from_hub():
    auth = _auth()
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(return_value=httpx.Response(401))
        user = await auth.authenticate("bogus-token")
    assert user is None


async def test_authenticate_raises_403_when_scope_missing():
    auth = _auth()
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(
            return_value=httpx.Response(200, json={"name": "alice", "scopes": ["self"]})
        )
        with pytest.raises(HTTPException) as excinfo:
            await auth.authenticate("alice-token")
    assert excinfo.value.status_code == 403


async def test_authenticate_propagates_403_from_hub():
    auth = _auth()
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(return_value=httpx.Response(403))
        with pytest.raises(HTTPException) as excinfo:
            await auth.authenticate("denied-token")
    assert excinfo.value.status_code == 403


async def test_authenticate_502_on_unexpected_status():
    auth = _auth()
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(return_value=httpx.Response(500))
        with pytest.raises(HTTPException) as excinfo:
            await auth.authenticate("token")
    assert excinfo.value.status_code == 502


async def test_authenticate_caches_user_for_token():
    auth = _auth()
    with respx.mock:
        route = respx.get(f"{HUB_API}/user").mock(
            return_value=httpx.Response(
                200, json={"name": "alice", "scopes": ["custom:publishing"]}
            )
        )
        await auth.authenticate("alice-token")
        await auth.authenticate("alice-token")
    assert route.call_count == 1


async def test_authenticate_honours_filtered_scope():
    """check_scopes correctly handles filter syntax (`scope!filter=value`).

    The required scope is the bare `read:users`; the caller holds the
    *filtered* `read:users!group=class-a`. JupyterHub's check_scopes
    treats the latter as authorising the former for users matching the
    filter, but for our `required_scopes` semantics the bare scope is
    asking "do you hold any subset". This test pins down the behavior
    we ship rather than relying on intuition.
    """
    auth = _auth(required_scopes={"read:users"})
    with respx.mock:
        respx.get(f"{HUB_API}/user").mock(
            return_value=httpx.Response(
                200,
                json={"name": "alice", "scopes": ["read:users!group=class-a"]},
            )
        )
        user = await auth.authenticate("alice-token")
    assert user is not None


async def test_authority_required():
    with pytest.raises(Exception):
        # No authority set; should fail when traitlets tries to use it.
        # The actual failure surfaces when User is constructed at
        # authenticate time, so trigger that path:
        auth = HubAuthenticator(hub_api_url=HUB_API)
        with respx.mock:
            respx.get(f"{HUB_API}/user").mock(
                return_value=httpx.Response(
                    200, json={"name": "alice", "scopes": ["custom:publishing"]}
                )
            )
            await auth.authenticate("alice-token")


async def test_falls_back_to_jupyterhub_api_url_env(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_API_URL", HUB_API)
    auth = HubAuthenticator(authority=AUTHORITY)
    assert auth.hub_api_url == HUB_API


async def test_raises_if_no_hub_api_url(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_API_URL", raising=False)
    with pytest.raises(ValueError):
        HubAuthenticator(authority=AUTHORITY)
