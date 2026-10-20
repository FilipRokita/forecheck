import pytest

from forecheck.infrastructure.database_url import to_sqlalchemy_url


@pytest.mark.parametrize("scheme", ["postgresql", "postgres", "postgresql+psycopg"])
def test_provider_schemes_become_psycopg_3(scheme: str) -> None:
    assert to_sqlalchemy_url(f"{scheme}://u:p@host/db?sslmode=require") == (
        "postgresql+psycopg://u:p@host/db?sslmode=require"
    )


@pytest.mark.parametrize("url", ["mysql://u@h/db", "u:p@host/db", ""])
def test_other_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="Database URL"):
        to_sqlalchemy_url(url)
