# Proposal: backend integration with one or more JupyterHubs (and standalone Jupyter)

## Context

`jupyter-publish-service` is a backend-only sharing service. The sharing UI lives inside JupyterLab; the service exposes a REST API. Authentication today is a single pluggable `JWTAuthenticator`. The default user store searches publish-service's own SQL database.

This proposal adds **JupyterHub as a first-class authentication and identity source**, and at the same time generalizes the design so a single publish-service deployment can front **one or more Jupyter installations** of any kind — standalone JupyterLab, JupyterLite, and JupyterHub — without forcing a Hub on deployments that don't have one.

## The core idea: per-authority identity, central sharing

Each Jupyter deployment is registered with publish-service under an admin-supplied `authority` value. Identities in publish-service are `(authority, username)`. The service maintains a registry of trusted authorities and the means to validate tokens minted by each. UI surfaces always render the qualified `alice@hub-research.example.com` form so collisions across deployments are unambiguous.

### What is an `authority`?

- **Admin-supplied.** The operator picks the value when registering a Jupyter deployment with publish-service, and configures the matching value on the Jupyter side.
- **Format is not prescribed.** A domain (`hub.example.com`), a subdomain (`research.hub.example.com`), or an opaque short name (`hub-research`) all work. publish-service treats it as an opaque, case-sensitive string.
- **Immutable once set.** All `User` and `Collaborator` rows are keyed against it; renaming requires a deliberate migration. Operators should pick a stable value on day one.
- **Globally unique within a publish-service deployment.** Two registered authorities must use distinct values. Domain-shaped values get this for free.

```
   JupyterLab                       JupyterHub A                       JupyterHub B
   authority=lab.example.com        authority=hub-a.example.com        authority=hub-b.example.com
   user: alice                      users: alice, bob                  users: alice, carol
        │                                  │                                   │
        │ X-Jupyter-Authority:             │ X-Jupyter-Authority:              │ X-Jupyter-Authority:
        │   lab.example.com                │   hub-a.example.com               │   hub-b.example.com
        │ Authorization: Bearer <jwt>      │ Authorization: Bearer <hub-tok>   │ Authorization: Bearer <hub-tok>
        └──────────────┬───────────────────┴──────────────────┬────────────────┘
                       ▼                                      ▼
              ┌──────────────────────────────────────────────────┐
              │             jupyter-publish-service              │
              │  ┌────────────────────────────────────────────┐  │
              │  │  Authority registry                        │  │
              │  │   lab.example.com   → JWTAuthenticator(…)  │  │
              │  │   hub-a.example.com → HubAuthenticator(…)  │  │
              │  │   hub-b.example.com → HubAuthenticator(…)  │  │
              │  └────────────────────────────────────────────┘  │
              │  Users:                                          │
              │   (lab.example.com,   alice),                    │
              │   (hub-a.example.com, alice),                    │
              │   (hub-a.example.com, bob),                      │
              │   (hub-b.example.com, alice), …                  │
              │  Shares may include collaborators from any       │
              │  registered authority.                           │
              └──────────────────────────────────────────────────┘
```

A cross-authority share: `alice@hub-a.example.com` adds `carol@hub-b.example.com` and `alice@lab.example.com` as collaborators on a notebook. Each appears in their own JupyterLab as a share they have access to, the next time they authenticate.

## Why this generalizes well

- **Standalone JupyterLab** keeps the existing `JWTAuthenticator` path. A Hub is not required.
- **A single JupyterHub** is the multi-authority design with N=1; no extra machinery surfaces to the operator.
- **Multiple JupyterHubs** drop in as additional registry entries.
- **JupyterLite** is just another authority with its own auth choice (typically a JWT or signed bearer).
- The same `(authority, username)` identity is reusable by any future surface the publish-service grows beyond the current REST API.

## Architecture

### Identity

```python
# jupyter_publishing_service/models/sql.py
class User(SQLModel, table=True):
    authority: str = Field(primary_key=True)
    username:  str = Field(primary_key=True)
    name:         Optional[str] = None
    display_name: Optional[str] = None
    initials:     Optional[str] = None
    avatar_url:   Optional[str] = None
    color:        Optional[str] = None

    @property
    def qualified_name(self) -> str:
        return f"{self.username}@{self.authority}"


class Collaborator(SQLModel, table=True):
    authority: str = Field(primary_key=True)
    username:  str = Field(primary_key=True)
    file:      str = Field(foreign_key="sharedfilemetadata.id", primary_key=True)
    role:      str = Field(foreign_key="role.name")
    __table_args__ = (
        ForeignKeyConstraint(
            ["authority", "username"],
            ["user.authority", "user.username"],
        ),
    )
```

`User` rows are inserted only on first appearance in a share — they are never pre-synced from a Hub. The authority registry is consulted to *verify* the caller (via the authenticator) and to *search* for collaborators (via the user store). The DB is the canonical record of who is mentioned in a share.

### Authority registry

```python
# jupyter_publishing_service/authority/registry.py
class AuthorityConfig(BaseModel):
    name: str                       # admin-supplied, immutable, e.g. "hub-research.example.com"
    authenticator_class: Any        # class object or dotted path
    authenticator_config: dict = {}
    user_store_class: Optional[Any] = None        # defaults to SQLUserStore
    user_store_config: dict = {}
    hosts: list[str] = []           # for Host-header fallback resolution


class AuthorityRegistry(LoggingConfigurable):
    def __init__(self, configs: list[AuthorityConfig], *, storage_manager=None, **kw): ...

    def resolve(self, request: Request) -> _BoundAuthority:
        name = request.headers.get("X-Jupyter-Authority")
        if name:
            return self._by_name[name]               # raises 401 if unknown
        host = request.headers.get("host", "").split(":")[0]
        if host in self._by_host:
            return self._by_host[host]
        raise HTTPException(401, "Unknown or missing authority")
```

Each registered authority is constructed once at startup into a `_BoundAuthority` — an authenticator and a user store with that authority's value baked in. This avoids leaking per-request authority into nested classes; the only two classes that need it (`HubAuthenticator`/`JWTAuthenticator` and `HubUserStore`/`SQLUserStore`) get it at construction time.

Example operator config:

```python
c.JupyterPublishingService.authorities = [
    {
        "name": "hub-research.example.com",
        "authenticator_class": "jupyter_publishing_service.authenticator.hub.HubAuthenticator",
        "authenticator_config": {
            "hub_api_url": "https://hub-research.example.com/hub/api",
        },
        "user_store_class": "jupyter_publishing_service.user.hub.HubUserStore",
        "hosts": ["hub-research.example.com"],
    },
    {
        "name": "lab.example.com",
        "authenticator_class": "jupyter_publishing_service.authenticator.jwt.JWTAuthenticator",
        "authenticator_config": {
            "public_key_url": "https://idp.example.com/.well-known/jwks.json",
        },
        # user_store_class omitted → defaults to SQLUserStore bound to this authority
    },
]
```

### Request flow

```
                       ┌─────────────────────┐
                       │ request enters API  │
                       │ X-Jupyter-Authority │
                       │ Authorization: …    │
                       └──────────┬──────────┘
                                  ▼
                  AuthorityRegistry.resolve(req)
                                  │ (header → host fallback → 401)
                                  ▼
                bound.authenticator.authenticate(token)
                                  │ → User(authority, username, …)
                                  ▼
              request.state.user = user
              request.state.authority = bound
                                  │
                                  ▼
                      route handler runs
```

```python
# jupyter_publishing_service/routes.py
async def authenticate(request: Request) -> User:
    creds = await httpBearer(request)
    if creds.scheme.lower() != "bearer":
        raise HTTPException(403, "Unsupported authentication method")
    bound = router.app.authority_registry.resolve(request)
    user = await bound.authenticator.authenticate(creds.credentials)
    if not user:
        raise HTTPException(401, "Unauthorized")
    request.state.user = user
    request.state.authority = bound
    return user
```

### `HubAuthenticator`

JupyterHub tokens are opaque strings, not JWTs; the Hub is the only authority that can validate them. The authenticator calls `GET /hub/api/user` with the caller's bearer, runs the response through `jupyterhub.services.auth.check_scopes` (which correctly handles filter syntax like `read:users!group=class-a` that a naive `in`-check gets wrong), and returns a `User` stamped with the bound authority. Successful validations are cached for 5 minutes per token, mirroring `HubAuth._cache_max_age`.

Per-authority configuration; `$JUPYTERHUB_API_URL` is honoured as a last-resort default so a single-Hub deployment under a managed-service env works out of the box.

### `HubUserStore`

Powers `GET /sharing/users` for Hub-fronted authorities. Calls `GET /hub/api/users` with `name_filter` and `offset`/`limit` pagination. Uses the **service-owned** Hub API token (granted `list:users` and `read:users` in `c.JupyterHub.load_roles` with `services: ["publish"]`) so individual users do not need `list:users` themselves. A 403 from the Hub falls back to an empty list. An alternative implementation that delegates user-search to the request token (so results inherit per-user permissions) is straightforward to swap in.

### JupyterHub-side configuration

The publish-service registers as an **external** service — no `command`, no `url`, so the Hub does not start or proxy to it. The two processes share an `api_token`. The service is granted `list:users`/`read:users`; users are granted `custom:publishing`.

```python
# jupyterhub_config.py
from jupyter_publishing_service.constants import JUPYTERHUB_SCOPE  # "custom:publishing"

c.JupyterHub.custom_scopes = {
    JUPYTERHUB_SCOPE: {"description": "Access the publishing service."},
}

c.JupyterHub.services = [
    {"name": "publish", "api_token": os.environ["PUBLISH_SERVICE_API_TOKEN"]},
]

c.JupyterHub.load_roles = [
    {
        "name": "publish-service-role",
        "scopes": ["list:users", "read:users"],
        "services": ["publish"],
    },
    {"name": "user", "scopes": ["self", JUPYTERHUB_SCOPE]},
]
```

### Client side

A jupyter-server extension running inside the user's single-user server is the HTTP client. For Hub-spawned servers, `JUPYTERHUB_API_TOKEN` identifies the user (the request to `/hub/api/user` returns the owning user's model) and the Spawner's environment carries `JUPYTER_AUTHORITY` matching publish-service's registry:

```python
client = AsyncPublishingClient(
    service_url=os.environ["PUBLISH_SERVICE_URL"],
    api_token=os.environ["JUPYTERHUB_API_TOKEN"],
    extra_headers={"X-Jupyter-Authority": os.environ["JUPYTER_AUTHORITY"]},
)
```

Standalone JupyterLab presents whatever token its configured authenticator expects (typically an SSO-issued JWT) and the matching `X-Jupyter-Authority` value.

### Cross-authority shares

When `alice@hub-a.example.com` adds `carol@hub-b.example.com` to a share:

1. The sharing dialog searches users in alice's own authority. To address carol, alice types `carol@hub-b.example.com` directly (cross-authority federated search lands in a follow-up).
2. publish-service receives `POST /sharing` with `users: [{authority: "hub-b.example.com", username: "carol"}]`.
3. publish-service writes a `User(authority="hub-b.example.com", username="carol")` row if absent, plus a `Collaborator` linking carol to the file.
4. When carol next authenticates against publish-service via hub-b, her `(hub-b.example.com, carol)` identity matches the existing row and the share appears in her file list.

publish-service trusts the inserting caller's claim that `(hub-b.example.com, carol)` is a valid identity in hub-b. It never independently verifies that claim until carol shows up with a hub-b token; if she never does, the row is harmless. Operators who want stricter inbound-share semantics can disable cross-authority shares entirely (see *Open questions*).

## Risks

- **Scope filter semantics.** Hub scopes can carry filters (`read:users!group=class-a`). Naive `in`-checks pass-or-fail incorrectly. Using `jupyterhub.services.auth.check_scopes` eliminates the bug class — adding `jupyterhub` as a dependency is the cost.
- **Token cache invalidation.** Hub tokens can be revoked. A 5-minute TTL is acceptable for sharing operations and matches the `HubAuth` default; the cache window is configurable.
- **Header spoofing.** `X-Jupyter-Authority` is client-supplied. The registry rejects unknown values; an attacker cannot route to an authority that isn't registered, and the token must still validate against *that* authority's hub. The host-header fallback is allowlist-only.
- **Cross-authority sharing trust.** Inserting a `User` row on first appearance accepts the sharer's claim that the collaborator exists. Mitigated by an `allowed_collaborator_authorities` knob (planned) and by the fact that an unconfirmed row only matters if the named user actually authenticates.
- **Operational footprint.** N hubs means N service tokens in publish-service's environment. The Helm chart can ship a `valuesFrom` pattern that mounts a secret per authority.
- **Authority renaming.** Authority values are immutable once a deployment is live; renaming requires a deliberate migration. Pick the value carefully on day one.

## Open questions

1. **Authority value choice.** The operator picks the value freely. Should the example configs strongly suggest a domain-shaped value for new deployments, or stay neutral? Recommend strong suggestion of a domain shape in docs without enforcing it in code.
2. **Federated user search.** Should a search hit every registered authority and return the union, or stay scoped to the caller's authority with manual `username@authority` entry for cross-authority shares? Recommend per-authority for now, federated as a follow-up.
3. **Authorization model.** Keep the existing role-based model (READER/WRITER/EXECUTOR) unchanged, or layer authority-level policies (e.g. "authority hub-a does not accept inbound shares from authority hub-b")? Recommend keeping roles as-is initially and adding authority-level policy as a separate proposal if needed.

## Phased rollout

**Phase 1 — Multi-authority registry and Hub authentication.** `HubAuthenticator`, `(authority, username)` schema, `AuthorityRegistry` with header-based routing (host fallback), `HubUserStore`, example showing one Hub and one standalone JupyterLab side by side. Single-authority deployments use a one-entry list.

**Phase 2 — Federated user search and cross-authority share policy.** A user search hits every authority registered with this publishing-service deployment and returns the union; the JupyterLab sharing dialog stays unchanged (no per-authority picker — the publishing service does the fan-out). Add `allowed_collaborator_authorities` so operators can opt out of inbound shares from specific authorities.

## References

- JupyterHub services API: `jupyterhub/services/auth.py` (`HubAuth`, `HubOAuth`, `check_scopes`)
- JupyterHub scopes: `jupyterhub/scopes.py`; JupyterHub docs `rbac/scopes.md`
- Reference external service: `examples/service-fastapi/` in the JupyterHub repository
