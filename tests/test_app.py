import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from traitlets.config import Config

from jupyter_publishing_service.app import JupyterPublishingService
from jupyter_publishing_service.models.rest import SharedFileRequestModel

from .mock import (
    COLLABORATORS,
    MockNoOpAuthenticator,
    MockNoOpAuthorizer,
    mock_shared_notebook_content,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def service():
    # In memory path.
    db_file = "sqlite+aiosqlite://"
    service = JupyterPublishingService(
        authenticator_class=MockNoOpAuthenticator,
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
        collaborators=[COLLABORATORS[0], COLLABORATORS[1]],
        roles=[{"name": "WRITERS"}],
        contents=contents,
    )

    async with async_client as client:
        resp = await client.post("/sharing", content=request_model.model_dump_json())
    assert resp.status_code == 200
