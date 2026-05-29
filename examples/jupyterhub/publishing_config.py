"""Publishing service configuration with two authorities side by side:
one JupyterHub deployment and one standalone JupyterLab deployment.

A single publishing service receives requests from both, distinguishes
them by the X-Jupyter-Authority header (or Host header fallback), and
validates each request against that authority's authenticator. Users
from either side may be added as collaborators on the other side's
shares; their identities never collide because each User row carries
its `authority`.

To run only one of them, drop the other entry from `authorities`.

Environment variables read here:

    JUPYTER_HUB_API_URL    - Base URL for the Hub REST API
                             (default: http://localhost:8000/hub/api).
    JUPYTERHUB_API_TOKEN   - Same value as `PUBLISH_SERVICE_API_TOKEN`
                             in hub_config.py. Used by HubAuthenticator
                             and HubUserStore as the service token.
    LAB_JWKS_URL           - JWKS URL for verifying tokens from the
                             standalone JupyterLab side.
"""
import os

# --- Authority 1: JupyterHub --------------------------------------------------
hub_authority = {
    # Operator-supplied identifier for this Jupyter deployment. Stamped
    # onto every User originating from it. Treat as immutable once data
    # exists; pick something stable.
    "name": "hub-local",
    "authenticator_class": (
        "jupyter_publishing_service.authenticator.hub.HubAuthenticator"
    ),
    "authenticator_config": {
        "hub_api_url": os.environ.get(
            "JUPYTER_HUB_API_URL", "http://localhost:8000/hub/api"
        ),
    },
    "user_store_class": "jupyter_publishing_service.user.hub.HubUserStore",
    "user_store_config": {
        "hub_api_url": os.environ.get(
            "JUPYTER_HUB_API_URL", "http://localhost:8000/hub/api"
        ),
        # service_api_token defaults to $JUPYTERHUB_API_TOKEN.
    },
    # Host fallback: requests without X-Jupyter-Authority but
    # with a matching Host header are routed here.
    "hosts": ["localhost"],
}

# --- Authority 2: standalone JupyterLab ---------------------------------------
# A non-Hub Jupyter deployment whose users authenticate via JWTs issued
# by some upstream identity provider (corporate SSO, Auth0, Google, etc.).
# The publishing service verifies signatures against the IdP's JWKS URL.
# Users are searched out of the publishing service's own DB
# (SQLUserStore is the default if `user_store_class` is omitted), so
# only users who have already been added to a share will appear in the
# autocomplete; that's expected for non-Hub deployments.
lab_authority = {
    "name": "lab-local",
    "authenticator_class": (
        "jupyter_publishing_service.authenticator.jwt.JWTAuthenticator"
    ),
    "authenticator_config": {
        "public_key_url": os.environ.get(
            "LAB_JWKS_URL", "https://idp.example.com/.well-known/jwks.json"
        ),
    },
    # No user_store_class -> defaults to SQLUserStore bound to this authority.
    "hosts": ["lab.local"],
}

c.JupyterPublishingService.authorities = [hub_authority, lab_authority]
