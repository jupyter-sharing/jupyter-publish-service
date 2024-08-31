import os
import socket

import uvicorn
from fastapi import FastAPI
from jupyter_core.application import JupyterApp
from jupyter_core.paths import jupyter_data_dir
from traitlets import Instance, Integer, Type, Unicode, default, validate

from jupyter_publishing_service.authenticator.jwt_authenticator import (
    AuthenticatorABC,
    JWTAuthenticator,
)
from jupyter_publishing_service.authenticator.service import set_authenticator_class
from jupyter_publishing_service.authorizer.rbac_authorizer import (
    AuthorizerABC,
    RBACAuthorizer,
)
from jupyter_publishing_service.authorizer.service import set_authorizer_class
from jupyter_publishing_service.routes import router
from jupyter_publishing_service.storagemanager import (
    BaseStorageManager,
    SQLStorageManager,
)

DEFAULT_SHARING_FOLDER = os.path.join(jupyter_data_dir(), "publishing")
DEFAULT_JUPYTER_PUBLISHING_PORT = 9000


class JupyterPublishingService(JupyterApp):

    name = "publishing"
    description = (
        "A Jupyter service for publishing notebooks and sharing them with Jupyter servers."
    )

    authenticator_class = Type(
        default_value=JWTAuthenticator,
        kclass="jupyter_publishing_service.authenticator.abc.AuthenticatorABC",
    ).tag(config=True)

    authorizer_class = Type(
        default_value=RBACAuthorizer,
        kclass="jupyter_publishing_service.authorizer.abc.AuthorizerABC",
    ).tag(config=True)

    storage_manager_class = Type(
        default_value=SQLStorageManager,
        kclass="jupyter_publishing_service.storagemanager.BaseStorageManager",
    ).tag(config=True)

    root_dir = Unicode(default_value=DEFAULT_SHARING_FOLDER).tag(config=True)

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

    authorizer: AuthorizerABC = Instance(
        klass="jupyter_publishing_service.authorizer.abc.AuthorizerABC", allow_none=True
    )

    storage_manager: BaseStorageManager = Instance(
        klass="jupyter_publishing_service.storagemanager.BaseStorageManager", allow_none=True
    )

    def init_configurables(self):
        self.authenticator = self.authenticator_class(parent=self, log=self.log)
        self.authorizer = self.authorizer_class(parent=self, log=self.log)
        set_authenticator_class(self.authenticator)
        set_authorizer_class(self.authorizer)
        self.storage_manager = self.storage_manager_class(parent=self, log=self.log)
        self.storage_manager.initialize()

    def init_webapp(self):
        self.app = FastAPI(
            title="Jupyter Publishing Server",
            description="Jupyter File Publishing Server implementation powered by FastAPI.",
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
