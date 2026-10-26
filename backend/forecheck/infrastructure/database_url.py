"""Turn the connection strings database providers hand out into SQLAlchemy URLs."""

_DRIVER = "postgresql+psycopg"
_SCHEMES = ("postgresql", "postgres", "postgresql+psycopg")


def to_sqlalchemy_url(url: str) -> str:
    """Return ``url`` with the psycopg 3 driver in its scheme.

    Providers hand out ``postgres://`` or ``postgresql://``, and SQLAlchemy would
    pick the old psycopg2 driver for those. Anything else is rejected, so a typo
    fails at start-up instead of at the first query.
    """
    scheme, separator, rest = url.partition("://")
    if not separator or scheme not in _SCHEMES:
        raise ValueError(
            "Database URL must start with postgresql://, postgres:// or postgresql+psycopg://"
        )
    return f"{_DRIVER}://{rest}"
