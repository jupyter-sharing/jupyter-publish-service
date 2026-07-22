"""Tests for the authority registry."""
from typing import Optional
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from jupyter_publishing_service.authority.registry import (
    AuthorityConfig,
    AuthorityRegistry,
    _BoundAuthority,
)
from jupyter_publishing_service.models.sql import User

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _StubAuth:
    def __init__(self, *, authority, **_kwargs):
        self.authority = authority

    async def authenticate(self, token: str) -> Optional[User]:
        return User(authority=self.authority, username="alice") if token else None


class _StubUserStore:
    def __init__(self, *, authority, **_kwargs):
        self.authority = authority

    async def search_users(self, _substring):
        return []


def _cfg(**overrides):
    base = {
        "name": "auth-a",
        "authenticator_class": _StubAuth,
        "user_store_class": _StubUserStore,
    }
    base.update(overrides)
    return AuthorityConfig.model_validate(base)


def _request(*, authority_header=None, host=None):
    headers: dict = {}
    if authority_header is not None:
        headers["X-Jupyter-Authority"] = authority_header
    if host is not None:
        headers["host"] = host
    req = Mock()
    req.headers = headers
    return req


def test_registry_resolves_by_header():
    reg = AuthorityRegistry(configs=[_cfg(name="a"), _cfg(name="b")])
    bound = reg.resolve(_request(authority_header="b"))
    assert bound.name == "b"


def test_registry_resolves_by_host_fallback():
    reg = AuthorityRegistry(
        configs=[
            _cfg(name="a", hosts=["a.example.com"]),
            _cfg(name="b", hosts=["b.example.com"]),
        ]
    )
    bound = reg.resolve(_request(host="b.example.com"))
    assert bound.name == "b"


def test_registry_strips_port_from_host():
    reg = AuthorityRegistry(configs=[_cfg(name="a", hosts=["a.example.com"])])
    bound = reg.resolve(_request(host="a.example.com:8443"))
    assert bound.name == "a"


def test_registry_rejects_unknown_authority_header():
    reg = AuthorityRegistry(configs=[_cfg(name="a")])
    with pytest.raises(HTTPException) as excinfo:
        reg.resolve(_request(authority_header="ghost"))
    assert excinfo.value.status_code == 401


def test_registry_rejects_when_no_header_and_no_host_match():
    reg = AuthorityRegistry(configs=[_cfg(name="a", hosts=["a.example.com"])])
    with pytest.raises(HTTPException) as excinfo:
        reg.resolve(_request(host="nope.example.com"))
    assert excinfo.value.status_code == 401


def test_registry_rejects_empty_config():
    with pytest.raises(ValueError):
        AuthorityRegistry(configs=[])


def test_registry_rejects_duplicate_name():
    with pytest.raises(ValueError):
        AuthorityRegistry(configs=[_cfg(name="a"), _cfg(name="a")])


def test_registry_rejects_duplicate_host():
    with pytest.raises(ValueError):
        AuthorityRegistry(
            configs=[
                _cfg(name="a", hosts=["x.example.com"]),
                _cfg(name="b", hosts=["x.example.com"]),
            ]
        )


def test_bound_authority_stamps_authority_on_authenticator():
    bound = _BoundAuthority(_cfg(name="a"))
    assert bound.authenticator.authority == "a"
    assert bound.user_store.authority == "a"


def test_authority_config_accepts_dotted_path():
    """Operators may pass a dotted-path string instead of a class object."""
    cfg = AuthorityConfig.model_validate(
        {
            "name": "a",
            "authenticator_class": "tests.test_authority_registry._StubAuth",
            "user_store_class": "tests.test_authority_registry._StubUserStore",
        }
    )
    bound = _BoundAuthority(cfg)
    assert bound.authenticator.authority == "a"
