import datetime
import uuid
from typing import List

from pydantic import BaseModel


class UserOrGroup(BaseModel):
    email: str


class Collaborator(BaseModel):
    id: str
    name: str
    email: str
    permissions: list


class SharedFile(BaseModel):
    id: uuid.UUID
    name: str
    author: str
    created: datetime.datetime
    last_modified: datetime.datetime
    version: int
    permissions: list
    sharable_link: str
    collaborators: List[Collaborator]
