import pytest
from pydantic import ValidationError

from forecheck.infrastructure.settings import Settings


def test_scores_are_kept_for_two_years_by_default() -> None:
    assert Settings(_env_file=None).score_retention_days == 730


def test_scores_cannot_be_kept_for_less_than_the_longest_period_the_page_shows() -> None:
    # The 12 months period reads 365 days back: a shorter retention would cut into what is shown.
    with pytest.raises(ValidationError):
        Settings(score_retention_days=364, _env_file=None)
    assert Settings(score_retention_days=365, _env_file=None).score_retention_days == 365
