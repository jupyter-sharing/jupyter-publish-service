import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from traitlets.config import Config

from jupyter_publishing_service.app import JupyterPublishingService
from jupyter_publishing_service.models.rest import SharedFileRequestModel

from .mock import (
    COLLABORATORS,
    TEST_AUTHORITY,
    MockNoOpAuthenticator,
    MockNoOpAuthorizer,
    MockUserStore,
    mock_shared_notebook_content,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def service():
    service = JupyterPublishingService(
        authorities=[
            {
                "name": TEST_AUTHORITY,
                "authenticator_class": MockNoOpAuthenticator,
                "user_store_class": MockUserStore,
                "hosts": ["test"],
            }
        ],
        config=Config(
            {
                "SQLStorageManager": {
                    "database_path": "sqlite+aiosqlite://",
                    "authorization_store_class": MockNoOpAuthorizer,
                }
            }
        ),
    )
    service.initialize()
    return service


@pytest.fixture
def app(service):
    return service.app


@pytest.fixture
def async_client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def start_db(service):
    await service.storage_manager.start()


def _auth_headers(token: str = "test-token"):
    return {
        "Authorization": f"Bearer {token}",
        "X-Jupyter-Authority": TEST_AUTHORITY,
    }


async def test_app(start_db, async_client):
    async with async_client as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"


async def test_create_file(start_db, async_client):
    metadata, contents = mock_shared_notebook_content(name="MockNotebook.ipynb")
    request_model = SharedFileRequestModel(
        metadata=metadata,
        users=[COLLABORATORS[0], COLLABORATORS[1]],
        roles=[{"name": "WRITER"}],
        contents=contents,
    )

    async with async_client as client:
        resp = await client.post(
            "/sharing",
            content=request_model.model_dump_json(),
            headers=_auth_headers(),
        )
    assert resp.status_code == 200


async def test_search_users_uses_bound_user_store(start_db, async_client):
    async with async_client as client:
        resp = await client.get("/sharing/users", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    # MockUserStore returns the canned collaborator list
    assert {u["username"] for u in body} == {c.username for c in COLLABORATORS}
    assert all(u["authority"] == TEST_AUTHORITY for u in body)


async def test_unknown_authority_header_rejected(start_db, async_client):
    async with async_client as client:
        resp = await client.get(
            "/sharing/users",
            headers={
                "Authorization": "Bearer test-token",
                "X-Jupyter-Authority": "no-such-authority",
            },
        )
    assert resp.status_code == 401
