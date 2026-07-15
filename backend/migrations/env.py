"""Alembic migration environment.

Deliberately does NOT reuse app.kernel.config.get_settings().database_url —
migrations run as the schema-owning Postgres role (able to CREATE TABLE,
CREATE ROLE, GRANT/REVOKE), while the application runs as a separate,
non-owning least-privilege role (0002_app_role_least_privilege.py; a
Postgres table owner bypasses GRANT/REVOKE and RLS regardless of what's
revoked from it — verified against a live Postgres, not assumed). Sharing
one connection string between the two would silently put migrations back
on the least-privilege role, breaking DDL, or the app back on the owning
role, breaking the whole point of 0002.

target_metadata is Base.metadata, populated by importing every context's
ORM module below so `alembic revision --autogenerate` can see the schema.
"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.contexts.identity.adapters.orm  # noqa: F401 — registers models with Base.metadata
from app.kernel.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("MIGRATIONS_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "MIGRATIONS_DATABASE_URL must be set — migrations run as the "
            "schema-owning role, never the app's least-privilege DATABASE_URL."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
