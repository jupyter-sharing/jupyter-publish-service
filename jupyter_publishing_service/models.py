import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Collaborator(SQLModel, table=True):
    name: str
    email: str = Field(primary_key=True)


class PermissionRoleLink(SQLModel, table=True):
    permission_name: str = Field(foreign_key="permission.name", primary_key=True)
    role_name: str = Field(foreign_key="role.name", primary_key=True)


class Role(SQLModel, table=True):
    name: str = Field(primary_key=True)
    permissions: list["Permission"] = Relationship(
        back_populates="roles", link_model=PermissionRoleLink
    )

    def permission_names(self):
        return [permission.name for permission in self.permissions]


class Permission(SQLModel, table=True):
    name: str = Field(primary_key=True)
    roles: list["Role"] = Relationship(back_populates="permissions", link_model=PermissionRoleLink)


class CollaboratorRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(foreign_key="collaborator.email", index=True)
    file: uuid.UUID = Field(foreign_key="sharedfile.id", index=True)
    role: str = Field(foreign_key="role.name")
    __table_args__ = (UniqueConstraint("email", "file", "role", name="unique_cfr"),)


class SharedFile(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    name: str
    author: str
    title: str
    created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_modified: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    version: int
    shareable_link: str


class JupyterContentsModel(BaseModel):
    name: str
    path: str
    type: str
    writable: str
    created: datetime
    last_modified: datetime
    mimetype: Optional[str] = None
    content: Optional[dict] = None
    format: Optional[str] = None


class CreateSharedFile(BaseModel):
    id: uuid.UUID
    author: str
    name: str
    title: str
    collaborators: List[Collaborator]
    notebook_server: Optional[str] = None
    # contents: JupyterContentsModel
    managed_by: Optional[str] = None
    roles: List[Role]
