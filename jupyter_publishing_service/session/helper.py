from datetime import datetime
from typing import List

import sqlalchemy.dialects.sqlite as sqllite
from sqlmodel import select

from jupyter_publishing_service.models import Collaborator, CollaboratorRole, SharedFile

# async def get_or_create_collaborator(session, model, defaults=None, **kwargs):
#     instance = session.query(model).filter_by(**kwargs).one_or_none()
#     if instance:
#         return instance, False
#     else:
#         kwargs |= defaults or {}
#         instance = model(**kwargs)
#         try:
#             session.add(instance)
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             instance = session.query(model).filter_by(**kwargs).one()
#             return instance, False
#         else:
#             return instance, True


async def create_or_update_collaborator(session, collaborator: Collaborator):
    current_collaborator = await session.get(Collaborator, collaborator.email)
    if current_collaborator is None:
        current_collaborator = collaborator
    setattr(current_collaborator, "name", collaborator.name)
    session.add(current_collaborator)
    await session.commit()
    await session.refresh(current_collaborator)

    return current_collaborator


async def create_or_update_file(session, file: SharedFile):
    current_file = await session.get(SharedFile, file.id)
    if current_file is None:
        current_file = file
    data = file.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(current_file, key, val)
    session.add(current_file)
    await session.commit()
    await session.refresh(current_file)

    return current_file


async def create_or_update_role(session, role: CollaboratorRole):
    statement = (
        select(CollaboratorRole)
        .where(CollaboratorRole.email == role.email)
        .where(CollaboratorRole.file == role.file)
        .where(CollaboratorRole.role == role.role)
    )
    result = await session.exec(statement)
    if result.first() is None:
        result = role
    for key, val in role.model_dump(exclude_unset=True).items():
        setattr(result, key, val)
    print(result)
    session.add(result)
    await session.commit()

    return result
