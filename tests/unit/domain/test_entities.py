from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from forecheck.domain.entities import Forecast, lead_days
from forecheck.domain.types import ModelId, StationId, Variable

STATION = StationId("12566")
MODEL = ModelId("icon")


def forecast(issued_at: datetime, valid: date, *, probability: float | None = None) -> Forecast:
    return Forecast(STATION, MODEL, Variable.TEMPERATURE, valid, issued_at, 10.0, probability)


def test_lead_is_counted_in_utc_days() -> None:
    issued = datetime(2026, 9, 8, 23, 59, tzinfo=UTC)
    assert lead_days(issued, date(2026, 9, 9)) == 1
    assert lead_days(issued, date(2026, 9, 15)) == 7


def test_lead_uses_the_utc_day_of_a_local_timestamp() -> None:
    # 01:30 on the 9th in Warsaw (UTC+2) is still the 8th in UTC.
    warsaw = timezone(timedelta(hours=2))
    assert lead_days(datetime(2026, 9, 9, 1, 30, tzinfo=warsaw), date(2026, 9, 10)) == 2


def test_a_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        lead_days(datetime(2026, 9, 8, 9, 0), date(2026, 9, 9))


@pytest.mark.parametrize("valid", [date(2026, 9, 8), date(2026, 9, 7), date(2026, 9, 16)])
def test_only_leads_one_to_seven_are_accepted(valid: date) -> None:
    with pytest.raises(ValueError, match="lead"):
        forecast(datetime(2026, 9, 8, 9, 0, tzinfo=UTC), valid)


def test_the_lead_is_exposed() -> None:
    assert forecast(datetime(2026, 9, 8, 9, 0, tzinfo=UTC), date(2026, 9, 11)).lead_days == 3


@pytest.mark.parametrize("probability", [-0.01, 1.01])
def test_a_probability_outside_zero_to_one_is_rejected(probability: float) -> None:
    with pytest.raises(ValueError, match="probability"):
        forecast(datetime(2026, 9, 8, 9, 0, tzinfo=UTC), date(2026, 9, 9), probability=probability)
