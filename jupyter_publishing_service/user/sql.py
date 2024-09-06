from typing import List

import cachetools
from sqlalchemy import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.sql import Collaborator
from jupyter_publishing_service.user.abc import UserStoreABC

cache = cachetools.TTLCache(maxsize=256, ttl=120)


class SQLUserStore(LoggingConfigurable):
    @cachetools.cached(cache)
    async def get_all_collaborators(self) -> List[Collaborator]:
        async with self.parent.get_session() as session:
            stmt = select(Collaborator)
            results = await session.exec(stmt)
            return results.all()

    async def search_users(self, search_string: str) -> List[Collaborator]:
        collaborators = await self.get_all_collaborators()
        names = [x for x in collaborators if x.name.startswith(search_string)]
        emails = [y for y in collaborators if y.email.startswith(search_string)]
        return names + emails

    async def search_groups(self, search_string: str) -> List[Collaborator]:
        return await self.search_users(search_string)


UserStoreABC.register(SQLUserStore)
