import pytest

from forecheck.infrastructure.settings import Settings


@pytest.mark.parametrize(
    ("app_url", "contact_email", "expected"),
    [
        ("", "", "forecheck/0.1"),
        ("https://example.org", "", "forecheck/0.1 (+https://example.org)"),
        ("", "me@example.org", "forecheck/0.1 (me@example.org)"),
        (
            "https://example.org",
            "me@example.org",
            "forecheck/0.1 (+https://example.org; me@example.org)",
        ),
    ],
)
def test_the_user_agent_names_only_what_the_operator_configured(
    app_url: str, contact_email: str, expected: str
) -> None:
    settings = Settings(app_url=app_url, contact_email=contact_email, _env_file=None)
    assert settings.user_agent == expected
