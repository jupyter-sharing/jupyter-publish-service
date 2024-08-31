from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from jupyter_publishing_service.models.sql import Permission, Role

async_engine = create_async_engine(
    f"sqlite+aiosqlite:///database.db",
    echo=True,
    future=True,
    connect_args={"check_same_thread": False},
)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def create_roles_and_permissions():
    reader = Role(name="READER")
    writer = Role(name="WRITER")
    executor = Role(name="EXECUTOR")
    read = Permission(name="READ", roles=[reader, writer, executor])
    write = Permission(name="WRITE", roles=[writer, executor])
    execute = Permission(name="EXECUTE", roles=[executor])
    async with get_session() as session:
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


async def create_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await create_roles_and_permissions()
