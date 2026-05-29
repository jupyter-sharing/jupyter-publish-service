from typing import List, Optional

from sqlalchemy import select
from traitlets import Unicode
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service.models.sql import User
from jupyter_publishing_service.user.abc import UserStoreABC


class SQLUserStore(LoggingConfigurable):
    """A user store that searches the publishing service's own user table.

    Bound to one `authority`; only returns users whose row carries the
    matching authority. Each per-authority registry entry that uses this
    store gets its own instance.

    Note that with the share-DB-only-after-creation rule, this store
    only sees users who have already been added to a share. Deployments
    that need a richer candidate set (e.g. a Hub with users who have
    not yet been in any share) should plug in a different user-store
    backend.
    """

    authority = Unicode(
        config=True,
        help="The authority this store filters on. Set by AuthorityRegistry.",
    )

    async def search_users(self, search_string: Optional[str]) -> List[User]:
        async with self.parent.get_session() as session:
            stmt = select(User).where(User.authority == self.authority)
            results = await session.exec(stmt)
            collaborators = [row[0] for row in results.all()]
        if search_string:
            return [u for u in collaborators if u.username.startswith(search_string)]
        return collaborators

    async def search_groups(self, search_string: Optional[str] = None) -> List[User]:
        return await self.search_users(search_string)


UserStoreABC.register(SQLUserStore)
