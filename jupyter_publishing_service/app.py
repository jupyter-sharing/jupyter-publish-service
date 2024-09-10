import os
import socket

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi as _get_openapi
from jupyter_core.application import JupyterApp
from traitlets import Instance, Integer, Type, Unicode, default, validate

from jupyter_publishing_service._version import __version__
from jupyter_publishing_service.authenticator.jwt_authenticator import JWTAuthenticator
from jupyter_publishing_service.authenticator.service import set_authenticator_class
from jupyter_publishing_service.authorizer.sqlrbac import AuthorizerABC
from jupyter_publishing_service.routes import lifespan, router
from jupyter_publishing_service.storage.abc import StorageManagerABC
from jupyter_publishing_service.storage.sql import SQLStorageManager

DEFAULT_JUPYTER_PUBLISHING_PORT = 9000


TITLE = "Jupyter Publishing Service"
SUMMARY = "A Jupyter service for publishing notebooks and sharing them with Jupyter servers."
DESCRIPTION = """
# Jupyter Publishing Service

* [Github repo](https://github.com/jupyter-sharing/jupyter-publish-service)
"""


def get_openapi_schema():
    return _get_openapi(
        title=TITLE,
        version=__version__,
        summary=SUMMARY,
        description=DESCRIPTION,
        routes=router.routes,
    )


class JupyterPublishingService(JupyterApp):

    name = "publishing"
    title = TITLE
    description = SUMMARY

    authenticator_class = Type(
        kclass="jupyter_publishing_service.authenticator.abc.AuthenticatorABC",
    ).tag(config=True)

    @default("authenticator_class")
    def _default_authenticator_class(self):
        return JWTAuthenticator

    storage_manager_class = Type(
        kclass="jupyter_publishing_service.storage.abc.StorageManagerABC",
    ).tag(config=True)

    @default("storage_manager_class")
    def _default_storage_manager_class(self):
        return SQLStorageManager

    port = Integer(
        DEFAULT_JUPYTER_PUBLISHING_PORT,
        config=True,
        help="Port of the server to be killed. Default %s" % DEFAULT_JUPYTER_PUBLISHING_PORT,
    )

    ip = Unicode(
        "localhost",
        config=True,
        help="The IP address the Jupyter server will listen on.",
    )

    @default("ip")
    def _default_ip(self):
        """Return localhost if available, 127.0.0.1 otherwise.
        On some (horribly broken) systems, localhost cannot be bound.
        """
        s = socket.socket()
        try:
            s.bind(("localhost", 0))
        except OSError as e:
            self.log.warning("Cannot bind to localhost, using 127.0.0.1 as default ip\n%s", e)
            return "127.0.0.1"
        else:
            s.close()
            return "localhost"

    @validate("ip")
    def _validate_ip(self, proposal):
        value = proposal["value"]
        if value == "*":
            value = ""
        return value

    authenticator: AuthorizerABC = Instance(
        klass="jupyter_publishing_service.authenticator.abc.AuthenticatorABC", allow_none=True
    )

    storage_manager: StorageManagerABC = Instance(
        klass="jupyter_publishing_service.storage.abc.StorageManagerABC", allow_none=True
    )

    def init_configurables(self):
        self.authenticator = self.authenticator_class(parent=self, log=self.log)
        set_authenticator_class(self.authenticator)
        self.storage_manager = self.storage_manager_class(parent=self, log=self.log)
        self.storage_manager.initialize()

    def init_webapp(self):
        self.app = FastAPI(
            title=TITLE,
            description=SUMMARY,
            lifespan=lifespan,
        )
        self.app.include_router(router)
        router.app = self

    def initialize(self, argv=[]):
        super().initialize(argv=argv)
        self.init_configurables()
        self.init_webapp()

    def start(self):
        super().start()
        # Make application available from globals
        uvicorn.run(self.app, host=self.ip, port=self.port)


main = JupyterPublishingService.launch_instance
