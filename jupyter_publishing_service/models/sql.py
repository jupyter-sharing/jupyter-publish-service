"""
SQL models for storing publishing data.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Collaborator(SQLModel, table=True):
    email: str = Field(primary_key=True)
    name: Optional[str]


class PermissionRoleLink(SQLModel, table=True):
    permission_name: str = Field(foreign_key="permission.name", primary_key=True)
    role_name: str = Field(foreign_key="role.name", primary_key=True)


class Role(SQLModel, table=True):
    name: str = Field(primary_key=True)
    permissions: List["Permission"] = Relationship(
        back_populates="roles", link_model=PermissionRoleLink
    )

    def permission_names(self):
        return [permission.name for permission in self.permissions]


class Permission(SQLModel, table=True):
    name: str = Field(primary_key=True)
    roles: List["Role"] = Relationship(back_populates="permissions", link_model=PermissionRoleLink)


class CollaboratorRole(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email: str = Field(foreign_key="collaborator.email", index=True)
    file: str = Field(foreign_key="sharedfilemetadata.id", index=True)
    role: str = Field(foreign_key="role.name")
    __table_args__ = (UniqueConstraint("email", "file", "role", name="unique_cfr"),)


class JupyterContentsModel(SQLModel, table=True):
    class Config:
        validate_assignment = True

    # NOTE: this field should never be set by the client.
    # This is used by the backend to map the file to its metadata.
    id: Optional[str] = Field(primary_key=True, description="A unique ID for a shared file.")
    name: str
    path: str
    type: str
    writable: bool
    created: datetime = Field(default_factory=datetime.now, nullable=False)
    last_modified: datetime = Field(default_factory=datetime.now, nullable=False)
    mimetype: Optional[str] = None
    content: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    format: Optional[str] = None


class SharedFileMetadata(SQLModel, table=True):
    id: str = Field(primary_key=True, description="A unique ID for a shared file.")
    author: Optional[str] = Field(
        description="The document's author's name. This should be a human readable name."
    )
    name: Optional[str] = Field(
        description="The name of the document; `Untitled.ipynb` probably isn't the best name ;)."
    )
    title: Optional[str] = Field(
        description="A human friendly title for this document that UIs can use."
    )
    created: Optional[datetime] = Field(default_factory=datetime.now, nullable=False)
    last_modified: Optional[datetime] = Field(default_factory=datetime.now, nullable=False)
    version: Optional[int] = Field(
        description="The version of this shared file. The version will be updated on every change of the file content."
    )
    shareable_link: Optional[str] = Field(
        description="A public link to share a static version of this notebook."
    )
    server_id: Optional[str] = Field(description="A unique ID of the server that 'owns' this file.")
