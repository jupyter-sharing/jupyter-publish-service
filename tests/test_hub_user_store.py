"""Tests for the JupyterHub-backed user store."""
import httpx
import pytest
import respx

from jupyter_publishing_service.user.hub import HubUserStore

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


HUB_API = "http://hub.test/hub/api"
AUTHORITY = "hub.test"
SERVICE_TOKEN = "service-token"


def _store(**overrides) -> HubUserStore:
    kwargs = {
        "authority": AUTHORITY,
        "hub_api_url": HUB_API,
        "service_api_token": SERVICE_TOKEN,
    }
    kwargs.update(overrides)
    return HubUserStore(**kwargs)


async def test_search_users_returns_all_when_no_filter():
    store = _store(page_size=10)
    with respx.mock:
        respx.get(f"{HUB_API}/users").mock(
            return_value=httpx.Response(
                200,
                json=[{"name": "alice"}, {"name": "bob"}],
            )
        )
        users = await store.search_users(None)
    assert [u.username for u in users] == ["alice", "bob"]
    assert all(u.authority == AUTHORITY for u in users)


async def test_search_users_forwards_name_filter():
    store = _store(page_size=10)
    with respx.mock:
        route = respx.get(f"{HUB_API}/users").mock(
            return_value=httpx.Response(200, json=[{"name": "alice"}])
        )
        await store.search_users("ali")
    assert route.calls[0].request.url.params["name_filter"] == "ali"


async def test_search_users_uses_service_token_not_caller_token():
    store = _store(page_size=10)
    with respx.mock:
        route = respx.get(f"{HUB_API}/users").mock(
            return_value=httpx.Response(200, json=[])
        )
        await store.search_users(None)
    assert route.calls[0].request.headers["Authorization"] == f"token {SERVICE_TOKEN}"


async def test_search_users_paginates():
    store = _store(page_size=2)
    with respx.mock:
        respx.get(f"{HUB_API}/users").mock(
            side_effect=[
                httpx.Response(200, json=[{"name": "alice"}, {"name": "bob"}]),
                httpx.Response(200, json=[{"name": "carol"}]),
            ]
        )
        users = await store.search_users(None)
    assert [u.username for u in users] == ["alice", "bob", "carol"]


async def test_search_users_returns_empty_on_403():
    store = _store(page_size=10)
    with respx.mock:
        respx.get(f"{HUB_API}/users").mock(return_value=httpx.Response(403))
        users = await store.search_users(None)
    assert users == []


async def test_requires_service_api_token(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_API_TOKEN", raising=False)
    with pytest.raises(ValueError):
        HubUserStore(authority=AUTHORITY, hub_api_url=HUB_API)


async def test_requires_hub_api_url(monkeypatch):
    monkeypatch.delenv("JUPYTERHUB_API_URL", raising=False)
    with pytest.raises(ValueError):
        HubUserStore(authority=AUTHORITY, service_api_token=SERVICE_TOKEN)


async def test_falls_back_to_env_vars(monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_API_URL", HUB_API)
    monkeypatch.setenv("JUPYTERHUB_API_TOKEN", SERVICE_TOKEN)
    store = HubUserStore(authority=AUTHORITY)
    assert store.hub_api_url == HUB_API
    assert store.service_api_token == SERVICE_TOKEN
