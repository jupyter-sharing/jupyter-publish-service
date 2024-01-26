from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.models import Permission, Role
from jupyter_publishing_service.traits import UnicodeFromEnv


class SessionManager(LoggingConfigurable):
    database_filepath = UnicodeFromEnv(
        name=constants.DATABASE_FILE,
        default_value="database.db",
        help=(
            "The filesystem path to SQLite Database file "
            "(e.g. /path/to/session_database.db). By default, the session "
            "database is stored on local filesystem disk"
        ),
    ).tag(config=True)

    _engine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sqlite_url = f"sqlite+aiosqlite:///{self.database_filepath}"
        connect_args = {"check_same_thread": False}
        self._engine = create_async_engine(
            sqlite_url, echo=True, future=True, connect_args=connect_args
        )

    async def create_db(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await self.create_roles_and_permissions()

    async def create_roles_and_permissions(self):
        reader = Role(name="READER")
        writer = Role(name="WRITER")
        executor = Role(name="EXECUTOR")
        read = Permission(name="READ", roles=[reader, writer, executor])
        write = Permission(name="WRITE", roles=[writer, executor])
        execute = Permission(name="EXECUTE", roles=[executor])
        async with self.get_session() as session:
            statement = select(Permission)
            results = await session.exec(statement)
            for perms in results:
                if perms.name == "READ":
                    return
            session.add(reader)
            session.add(writer)
            session.add(executor)
            session.add(read)
            session.add(write)
            session.add(execute)
            await session.commit()

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        async_session = sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session
