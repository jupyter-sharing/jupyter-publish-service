SSL_CERT_FILE = "SSL_CERT_FILE"
JWKS_URI = "JWKS_URI"
EMAIL_CLAIM_KEY = "EMAIL_CLAIM_KEY"

JUPYTERHUB_SCOPE = "custom:publishing"

# Header a client sends to identify which registered Jupyter deployment
# the request originates from. The publishing service matches the value
# against the authority registry to pick the right authenticator and
# user store; if absent, the Host header is used as a fallback per the
# `hosts` field on each authority entry.
AUTHORITY_HEADER = "X-Jupyter-Authority"

# Conventional env vars JupyterHub itself sets for managed services;
# HubAuthenticator and HubUserStore read these as defaults.
JUPYTERHUB_API_URL = "JUPYTERHUB_API_URL"
JUPYTERHUB_API_TOKEN = "JUPYTERHUB_API_TOKEN"
