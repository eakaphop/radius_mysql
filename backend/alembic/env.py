"""Alembic migration environment.

IMPORTANT: target_metadata is `Base.metadata`, which holds only the app_*
tables (admin_users, refresh_tokens, audit_log, bandwidth_profiles).
FreeRADIUS tables are modeled on the separate `FreeradiusBase` (see
app/db/models/freeradius_base.py) whose metadata is deliberately not exposed
here, so autogenerate can never produce a migration that touches them.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.db.models import Base
from app.db.session import engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    assert isinstance(engine, AsyncEngine)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
