"""Test fixtures and mocks shared across the test suite."""
from typing import List, Optional

from jupyter_publishing_service.authenticator.abc import AuthenticatorABC
from jupyter_publishing_service.authorizer.abc import AuthorizerABC
from jupyter_publishing_service.models.sql import (
    JupyterContentsModel,
    SharedFileMetadata,
    User,
)
from jupyter_publishing_service.user.abc import UserStoreABC

TEST_AUTHORITY = "test-authority"

COLLABORATORS: List[User] = [
    User(authority=TEST_AUTHORITY, username="alice@example.com", display_name="Alice"),
    User(authority=TEST_AUTHORITY, username="bob@example.com", display_name="Bob"),
    User(authority=TEST_AUTHORITY, username="carol@example.com", display_name="Carol"),
]


class MockNoOpAuthenticator:
    """Authenticator that approves any non-empty token as the first
    test collaborator. Used for happy-path API tests."""

    def __init__(self, *, authority: str = TEST_AUTHORITY, **kwargs):
        self.authority = authority

    async def authenticate(self, token: str) -> Optional[User]:
        if not token:
            return None
        return COLLABORATORS[0]


AuthenticatorABC.register(MockNoOpAuthenticator)


class MockNoOpAuthorizer:
    """Authorizer that allows every action. Used for tests that don't
    care about role-based access checks."""

    def __init__(self, *args, **kwargs):
        pass

    async def authorize(self, user: User, action: str, file_id: str) -> bool:
        return True


AuthorizerABC.register(MockNoOpAuthorizer)


class MockUserStore:
    """User store that returns the canned collaborator list."""

    def __init__(self, *, authority: str = TEST_AUTHORITY, **kwargs):
        self.authority = authority

    async def search_users(self, search_string: Optional[str]) -> List[User]:
        if not search_string:
            return COLLABORATORS
        return [u for u in COLLABORATORS if u.username.startswith(search_string)]

    async def search_groups(self, search_string: Optional[str] = None) -> List[User]:
        return []


UserStoreABC.register(MockUserStore)


def mock_shared_notebook_content(name: str = "MockNotebook.ipynb"):
    """Build a (metadata, contents) pair for a fake shared notebook."""
    metadata = SharedFileMetadata(
        id="file-1",
        author=COLLABORATORS[0].username,
        name=name,
        title=name,
        version=1,
    )
    contents = JupyterContentsModel(
        id="file-1",
        name=name,
        path=name,
        type="notebook",
        writable=True,
        mimetype="application/x-ipynb+json",
        format="json",
        content={"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5},
    )
    return metadata, contents
