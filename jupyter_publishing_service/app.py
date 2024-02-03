import os
import socket

import uvicorn
from fastapi import FastAPI
from jupyter_core.application import JupyterApp
from jupyter_core.paths import jupyter_data_dir
from traitlets import Integer, Type, Unicode, default, validate

from jupyter_publishing_service.authenticator.jwt_authenticator import JWTAuthenticator
from jupyter_publishing_service.authenticator.service import set_authenticator_class
from jupyter_publishing_service.authorizer.rbac_authorizer import RBACAuthorizer
from jupyter_publishing_service.authorizer.service import set_authorizer_class
from jupyter_publishing_service.collaborator.sql_collaborator import (
    SQLCollaboratorProvider,
)
from jupyter_publishing_service.file.sql_manager import SQLManager
from jupyter_publishing_service.routes import router

DEFAULT_SHARING_FOLDER = os.path.join(jupyter_data_dir(), "publishing")
DEFAULT_JUPYTER_PUBLISHING_PORT = 9000


class JupyterPublishingService(JupyterApp):
    authenticator_class = Type(
        default_value=JWTAuthenticator,
        kclass="jupyter_publishing_service.authenticator.AuthenticatorABC",
    ).tag(config=True)

    authorizer_class = Type(
        default_value=RBACAuthorizer,
        kclass="jupyter_publishing_service.authorizer.AuthorizerABC",
    ).tag(config=True)

    collaborator_store_class = Type(
        default_value=SQLCollaboratorProvider,
        klass="jupyter_publishing_service.collaborator.abc.CollaboratorStore",
    ).tag(config=True)

    file_manager_class = Type(
        default_value=SQLManager,
        klass="jupyter_server.services.contents.manager.ContentsManager",
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

    # database_filepath = UnicodeFromEnv(
    #     name=constants.DATABASE_FILE,
    #     default_value="database.db",
    #     help=(
    #         "The filesystem path to SQLite Database file "
    #         "(e.g. /path/to/session_database.db). By default, the session "
    #         "database is stored on local filesystem disk"
    #     ),
    # ).tag(config=True)

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

    def init_configurables(self):
        self.file_manager = self.file_manager_class(parent=self, log=self.log)
        self.collaborator_store = self.collaborator_store_class(parent=self, log=self.log)
        self.authenticator = self.authenticator_class(parent=self, log=self.log)
        self.authorizer = self.authorizer_class(parent=self, log=self.log)
        set_authenticator_class(self.authenticator)
        set_authorizer_class(self.authorizer)

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
