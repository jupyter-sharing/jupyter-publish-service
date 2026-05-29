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

# Only for local testing; remove in production.
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
    # Every hub user is allowed to use the publishing service.
    {
        "name": "user",
        "description": "Give all users access to the publishing service.",
        "scopes": ["self", JUPYTERHUB_SCOPE],
    },
]
