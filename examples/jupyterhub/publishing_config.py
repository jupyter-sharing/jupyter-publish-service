"""Use the JupyterHub authenticator to authenticate incoming
requests from users.
"""
from jupyter_publishing_service.authenticator.hub import HubAuthenticator

c.JupyterPublishingService.authenticator_class = HubAuthenticator
