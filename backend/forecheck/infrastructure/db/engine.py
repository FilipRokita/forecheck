"""Creating the database engine."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import NullPool

from forecheck.infrastructure.database_url import to_sqlalchemy_url


def create_db_engine(database_url: str) -> Engine:
    """An engine for a serverless host and a pooled (PgBouncer) connection string.

    - ``NullPool``: a function instance that is frozen between requests must not hold idle
      connections. The provider's pooler is what keeps connections cheap.
    - ``prepare_threshold=None``: psycopg would otherwise start server-side prepared
      statements after five uses, which a pooler in transaction mode cannot honour.
    """
    return create_engine(
        to_sqlalchemy_url(database_url),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )
