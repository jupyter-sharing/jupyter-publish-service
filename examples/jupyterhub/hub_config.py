"""Example JupyterHub configuration for fronting the publishing service.

This wires JupyterHub to the publishing service in three ways:

1. Defines a custom scope `custom:publishing` that gates access to the
   publishing service. Users must hold this scope.

2. Registers `publish` as an *external* service. JupyterHub does not
   spawn the publishing service (no `command` is set); instead the two
   processes share an `api_token`. Set `PUBLISH_SERVICE_API_TOKEN` in
   the environment of both `jupyterhub` and `jupyter-publishing`.

3. Grants `list:users` (and `read:users`) to the publishing service
   itself via `c.JupyterHub.load_roles`. The publishing service uses
   its own `api_token` to query `/hub/api/users` for the sharing-dialog
   autocomplete; the *user* doing the search does not need `list:users`.

   Note: an alternative model grants `list:users` to the `user` role
   and has the publishing service call `/hub/api/users` with the
   request token instead of its service token, so results inherit the
   caller's hub-level permissions. That requires a different user-store
   implementation; the design here is the simpler default.
"""
import os

from jupyter_publishing_service.constants import JUPYTERHUB_SCOPE

# Only for local testing; remove in production. The DummyAuthenticator
# accepts any username/password and does not require the user to exist
# as a system user (the default `PAMAuthenticator` would). `allow_all`
# additionally drops the explicit allowlist check.
c.JupyterHub.authenticator_class = "dummy"
c.Authenticator.allow_all = True

# Custom scope users hold to access the publishing service.
c.JupyterHub.custom_scopes = {
    JUPYTERHUB_SCOPE: {"description": "Access the Jupyter publishing service."},
}

# External service registration. No `command`, no `url` — JupyterHub
# does not start or proxy to the publishing service; the two share a
# pre-provisioned API token.
c.JupyterHub.services = [
    {
        "name": "publish",
        "api_token": os.environ["PUBLISH_SERVICE_API_TOKEN"],
    },
]

c.JupyterHub.load_roles = [
    # The publishing service can list and read users. Used by the
    # `HubUserStore` to back the sharing-dialog autocomplete.
    {
        "name": "publish-service-role",
        "description": "Lets the publishing service enumerate hub users.",
        "scopes": ["list:users", "read:users"],
        "services": ["publish"],
    },
]

# Optional: pre-mint API tokens for demo users when ALICE_TOKEN /
# BOB_TOKEN are set in the environment. Used by `run_demo.sh`.
#
# Wiring detail: `c.JupyterHub.api_tokens` mints the tokens for the
# named users (and creates the users on first run). We then declare a
# dedicated `publishing-user` role with the `custom:publishing` scope
# and explicitly assign it to those users; the default token role
# (`inherit`) on each token lets the token use whatever scopes its
# user has, including this one.
#
# We deliberately do NOT override the default `user` role here:
# overriding it loses the built-in user permissions (calling
# `/hub/api/user` returns empty scopes), which then trips the
# publish-service's scope check.
#
# Leave the env vars unset in real deployments.
_demo_users = {}
for _env, _user in (("ALICE_TOKEN", "alice"), ("BOB_TOKEN", "bob")):
    _value = os.environ.get(_env)
    if _value:
        _demo_users[_user] = _value
if _demo_users:
    c.JupyterHub.api_tokens = {token: user for user, token in _demo_users.items()}
    c.JupyterHub.load_roles.append(
        {
            "name": "publishing-user",
            "description": "Holds the custom publishing scope.",
            "scopes": [JUPYTERHUB_SCOPE],
            "users": list(_demo_users.keys()),
        }
    )
