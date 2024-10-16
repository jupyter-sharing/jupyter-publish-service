from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from traitlets import Bool, Instance, Unicode

from jupyter_publishing_service.models.sql import Permission, Role

from .abc import StorageManagerABC
from .base import BaseStorageManager


class SQLStorageManager(BaseStorageManager):

    database_path = Unicode(default_value="sqlite+aiosqlite:///database.db")
    _async_engine = Instance(AsyncEngine, allow_none=True)
    echo = Bool(default_value=False, help="Echo SQL queries for debugging.").tag(config=True)

    def initialize(self):
        self._async_engine = create_async_engine(
            self.database_path,
            echo=self.echo,
            future=True,
            connect_args={"check_same_thread": False},
        )
        super().initialize()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator:
        async_session = sessionmaker(
            self._async_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            yield session

    async def _create_roles_and_permissions(self):
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

    async def start(self):
        async with self._async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await self._create_roles_and_permissions()


StorageManagerABC.register(SQLStorageManager)
