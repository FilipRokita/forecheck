"""Alembic environment: runs the migrations against DIRECT_URL (or DATABASE_URL)."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from forecheck.infrastructure.database_url import to_sqlalchemy_url

config = context.config


def _url() -> str:
    # Migrations use the direct (unpooled) connection: a pooler in transaction
    # mode does not suit DDL. Locally DIRECT_URL stays empty.
    url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DIRECT_URL or DATABASE_URL to run the migrations.")
    return to_sqlalchemy_url(url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
