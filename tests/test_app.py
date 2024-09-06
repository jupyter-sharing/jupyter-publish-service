import pytest
from fastapi.testclient import TestClient
from traitlets.config import Config

from jupyter_publishing_service.app import JupyterPublishingService
from jupyter_publishing_service.authenticator.abc import AuthenticatorABC
from jupyter_publishing_service.authorizer.abc import AuthorizerABC


class MockAuthenticator:
    def __init__(self, *args, **kwargs):
        pass

    def authenticate(self, data):
        return {}


AuthenticatorABC.register(MockAuthenticator)


class MockAuthorizer:
    def __init__(self, *args, **kwargs):
        pass

    def authorize(self, data, file_id):
        return True


AuthorizerABC.register(MockAuthorizer)


@pytest.fixture
def service(tmp_path):
    db_file = "sqlite+aiosqlite://" + str(tmp_path.joinpath("database.db"))
    service = JupyterPublishingService(
        authenticator_class=MockAuthenticator,
        config=Config(
            {
                "SQLStorageManager": {
                    "database_path": db_file,
                    "authorization_store_class": MockAuthorizer,
                }
            }
        ),
    )
    return service


@pytest.fixture
def app(service):
    service.initialize()
    return service.app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_app(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"
