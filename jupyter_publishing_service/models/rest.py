"""
Pydantic models describing the REST API for this service.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from .sql import (
    Collaborator,
    CollaboratorRole,
    JupyterContentsModel,
    Role,
    SharedFileMetadata,
)


class ServiceStatusResponse(BaseModel):
    version: str
    status: str


class SharedFileRequestModel(BaseModel):
    """
    NOTE: There is a slight difference between the
    request model and the response model.
    The collaborators and roles models are separated
    in the request model for convenience.
    """

    metadata: SharedFileMetadata
    collaborators: Optional[List[Collaborator]] = None
    roles: Optional[List[Role]] = None
    contents: Optional[JupyterContentsModel] = None


class SharedFileResponseModel(BaseModel):
    """
    NOTE: There is a slight difference between the
    request model and the response model.
    The collaborators and roles models are separated
    in the request model for convenience.
    """

    metadata: SharedFileMetadata
    collaborator_roles: Optional[List[CollaboratorRole]] = None
    contents: Optional[JupyterContentsModel] = None
