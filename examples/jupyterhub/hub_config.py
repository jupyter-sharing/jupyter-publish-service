"""Example JupyterHub configuration for accessing the publishing service
using a JupyterHub user's API token generated from the JupyterHub API.

This is just meant as a starting example for local installation.

More advanced configurations using JupyterHub scopes/roles
are possible.
"""
from jupyter_publishing_service.constants import JUPYTERHUB_SCOPE

# Only for testing purposes.
c.Authenticator.allow_all = True

# Create a customer service
c.JupyterHub.custom_scopes = {
    JUPYTERHUB_SCOPE: {"description": "A scope defined for the publishing service."}
}
# Extend the default user role to give access to the publishing service.
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "description": "Give all users access to the publishing service.",
        "scopes": ["self", "custom:publishing"],
        "users": [],
        "services": [],
        "groups": [],
    }
]
