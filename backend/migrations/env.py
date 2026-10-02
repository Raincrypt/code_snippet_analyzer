import asyncio
from logging.config import fileConfig

from typing import Any

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base, UTCDateTime

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# The database URL comes from the app's settings (DATABASE_URL), not from alembic.ini.
DATABASE_URL = get_settings().database_url


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    """Migrations should not import app code: write our custom column type as plain SQL types."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False  # use Alembic's default rendering


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # render_as_batch lets SQLite apply ALTER TABLE changes (it supports very few natively).
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
