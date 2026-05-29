import os
import socket
from typing import List

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi as _get_openapi
from jupyter_core.application import JupyterApp
from traitlets import Instance, Integer, List as TList, Type, Unicode, default, validate

from jupyter_publishing_service._version import __version__
from jupyter_publishing_service.authority.registry import AuthorityConfig, AuthorityRegistry
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

    authorities = TList(
        trait=Instance(dict),
        default_value=[],
        config=True,
        help=(
            "List of authority configurations. Each entry registers a Jupyter "
            "deployment (a JupyterLab install, JupyterLite, or a JupyterHub) "
            "that may send requests to this publishing service. Supplied as "
            "dicts validated by AuthorityConfig:\n"
            "    {\n"
            "      'name': 'hub-research.example.com',\n"
            "      'authenticator_class': 'jupyter_publishing_service.authenticator.hub.HubAuthenticator',\n"
            "      'authenticator_config': {'hub_api_url': '…'},\n"
            "      'user_store_class': 'jupyter_publishing_service.user.hub.HubUserStore',\n"
            "      'user_store_config': {},\n"
            "      'hosts': ['hub-research.example.com'],\n"
            "    }\n"
            "Single-authority deployments configure a one-entry list. "
            "Each `name` is the operator-supplied authority value, "
            "stamped onto every User originating from that deployment. "
            "Required; immutable once data exists for a given authority."
        ),
    )

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

    storage_manager: StorageManagerABC = Instance(
        klass="jupyter_publishing_service.storage.abc.StorageManagerABC", allow_none=True
    )

    authority_registry: AuthorityRegistry = Instance(
        klass=AuthorityRegistry, allow_none=True
    )

    def init_configurables(self):
        if not self.authorities:
            raise ValueError(
                "JupyterPublishingService.authorities must contain at least "
                "one entry. Configure it in your publishing_config.py."
            )
        # Storage manager first: the SQLUserStore default needs it as parent
        # so it can share the database session.
        self.storage_manager = self.storage_manager_class(parent=self, log=self.log)
        self.storage_manager.initialize()
        configs = [AuthorityConfig.model_validate(entry) for entry in self.authorities]
        self.authority_registry = AuthorityRegistry(
            configs=configs,
            storage_manager=self.storage_manager,
            log=self.log,
        )

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
