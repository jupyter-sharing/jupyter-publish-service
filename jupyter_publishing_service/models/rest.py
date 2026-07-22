"""
Pydantic models describing the REST API for this service.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from .sql import JupyterContentsModel, Role, SharedFileMetadata, User


class ServiceStatusResponse(BaseModel):
    version: str
    status: str


class SharedFileRequestModel(BaseModel):
    """
    NOTE: There is a slight difference between the
    request model and the response model.

    The request model is mean to associate
    users with roles.

    A user->role relationship is a 'collaborator'.
    """

    metadata: SharedFileMetadata
    users: Optional[List[User]] = None
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
    collaborator: Optional[List[User]] = None
    contents: Optional[JupyterContentsModel] = None
