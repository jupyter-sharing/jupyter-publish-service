from typing import List, Optional

from aiocache import Cache, cached
from sqlalchemy import select
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.sql import Collaborator
from jupyter_publishing_service.user.abc import UserStoreABC


class SQLUserStore(LoggingConfigurable):
    """A user store that searches a list of
    all collaborators already in the publishing
    service database.
    """

    @cached(ttl=120, cache=Cache.MEMORY)
    async def get_all_collaborators(self) -> List[Collaborator]:
        async with self.parent.get_session() as session:
            stmt = select(Collaborator)
            results = await session.exec(stmt)
            records = results.all()
            collaborators = [row[0] for row in records]
        return collaborators

    async def search_users(self, search_string: Optional[str]) -> List[Collaborator]:
        collaborators = await self.get_all_collaborators()
        if search_string:
            return [x for x in collaborators if x.name.startswith(search_string)]
        return collaborators

    async def search_groups(self, search_string: Optional[str] = None) -> List[Collaborator]:
        return await self.search_users(search_string)


UserStoreABC.register(SQLUserStore)
