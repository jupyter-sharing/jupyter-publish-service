"""Authority registry: per-request lookup of which Jupyter deployment a
request came from, and the bound authenticator + user-search backend
configured for it.

Operators configure the publishing service with a list of authority
entries (one per Jupyter deployment that may send it requests). Each
entry is constructed once at startup into a `_BoundAuthority`: an
authenticator and a user-search store, both pre-wired with that
authority's value. At request time the registry resolves the incoming
`X-Jupyter-Authority` header (or, as a fallback, the `Host` header)
to the matching `_BoundAuthority`, and the route layer uses its
authenticator and user store to handle the request.

This shape avoids leaking the per-request authority value into the
internals of every class that needs it: the only classes that actually
need `authority` (the authenticator and the user store) get it baked
in at construction time. Nothing nested inside the storage manager
needs to know.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants


def _resolve_dotted(path: str):
    module_path, _, attr = path.rpartition(".")
    if not module_path:
        raise ValueError(f"Expected a dotted path, got {path!r}")
    module = import_module(module_path)
    return getattr(module, attr)


def _resolve_class(value):
    """Accept a class object or a dotted path string."""
    if isinstance(value, str):
        return _resolve_dotted(value)
    return value


class AuthorityConfig(BaseModel):
    """Operator-supplied configuration for one Jupyter deployment that
    sends requests to this publishing service."""

    name: str = Field(
        description="The authority value. Stamped onto every User row whose "
        "identity originated from this deployment. Operator-supplied; "
        "immutable once data exists for it. Format is not prescribed (a "
        "domain, subdomain, or opaque short name are all fine), but two "
        "registered authorities must have distinct values.",
    )
    authenticator_class: Any = Field(
        description="Class (or dotted path) implementing AuthenticatorABC.",
    )
    authenticator_config: Dict[str, Any] = Field(default_factory=dict)
    user_store_class: Optional[Any] = Field(
        default=None,
        description="Class (or dotted path) implementing UserStoreABC. "
        "Defaults to SQLUserStore (queries the publishing service's own DB).",
    )
    user_store_config: Dict[str, Any] = Field(default_factory=dict)
    hosts: List[str] = Field(
        default_factory=list,
        description="Host header values to fall back on when the request "
        "does not include X-Jupyter-Authority. Empty by default; set this "
        "if you want host-based routing as a backup.",
    )

    class Config:
        arbitrary_types_allowed = True


class _BoundAuthority:
    """A registered authority with its authenticator and user store
    instantiated and pre-wired."""

    def __init__(self, cfg: AuthorityConfig, *, parent_for_user_store=None):
        self.name = cfg.name

        Authenticator = _resolve_class(cfg.authenticator_class)
        self.authenticator = Authenticator(
            authority=cfg.name,
            **cfg.authenticator_config,
        )

        UserStore = _resolve_class(cfg.user_store_class) if cfg.user_store_class else None
        if UserStore is None:
            # Default: query the shared SQL user store for this authority.
            from jupyter_publishing_service.user.sql import SQLUserStore

            UserStore = SQLUserStore
        # SQLUserStore needs `parent` so it can call `parent.get_session()`;
        # external stores like HubUserStore do not. Pass parent only if the
        # store accepts one (LoggingConfigurable accepts arbitrary kwargs).
        kwargs = {"authority": cfg.name, **cfg.user_store_config}
        if parent_for_user_store is not None:
            kwargs["parent"] = parent_for_user_store
        self.user_store = UserStore(**kwargs)


class AuthorityRegistry(LoggingConfigurable):
    """Holds the set of registered authorities and resolves an incoming
    request to the right one."""

    def __init__(
        self,
        configs: List[AuthorityConfig],
        *,
        storage_manager=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not configs:
            raise ValueError(
                "JupyterPublishingService.authorities must contain at least "
                "one entry."
            )
        seen: set[str] = set()
        self._by_name: Dict[str, _BoundAuthority] = {}
        self._by_host: Dict[str, _BoundAuthority] = {}
        for cfg in configs:
            if cfg.name in seen:
                raise ValueError(f"Duplicate authority name: {cfg.name!r}")
            seen.add(cfg.name)
            bound = _BoundAuthority(cfg, parent_for_user_store=storage_manager)
            self._by_name[cfg.name] = bound
            for host in cfg.hosts:
                if host in self._by_host:
                    raise ValueError(
                        f"Host {host!r} is mapped to multiple authorities."
                    )
                self._by_host[host] = bound

    def resolve(self, request: Request) -> _BoundAuthority:
        name = request.headers.get(constants.AUTHORITY_HEADER)
        if name:
            bound = self._by_name.get(name)
            if bound is None:
                raise HTTPException(
                    status_code=401,
                    detail=f"Unknown authority: {name!r}",
                )
            return bound
        host = request.headers.get("host", "").split(":")[0]
        bound = self._by_host.get(host)
        if bound is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    f"Request did not include {constants.AUTHORITY_HEADER} "
                    f"and Host {host!r} is not mapped to a registered authority."
                ),
            )
        return bound

    def get(self, name: str) -> Optional[_BoundAuthority]:
        return self._by_name.get(name)

    def names(self) -> List[str]:
        return list(self._by_name.keys())
