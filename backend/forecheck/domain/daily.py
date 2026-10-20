"""Turning a day of station reports into one figure per variable.

Station data arrives hourly, forecasts arrive per day. These rules say when an
hourly series is complete enough to stand for a UTC day.
"""

from collections.abc import Mapping, Sequence

HOURS_PER_DAY = 24
# A mean over fewer reports than this is not trusted to represent the day.
MIN_HOURLY_REPORTS = 20
# Precipitation is reported as totals of the previous six hours, at these UTC hours.
# The total reported at 00 UTC covers the previous day's last six hours, so a UTC
# day is the 06, 12 and 18 UTC reports plus the 00 UTC report of the next day.
PRECIPITATION_REPORT_HOURS = (6, 12, 18, 24)


def daily_mean(
    hourly: Sequence[float | None], *, min_reports: int = MIN_HOURLY_REPORTS
) -> float | None:
    """Mean of the hourly values present, or ``None`` when too few of them are."""
    present = [value for value in hourly if value is not None]
    if len(present) < min_reports:
        return None
    return sum(present) / len(present)


def daily_precipitation(six_hour_totals: Mapping[int, float | None]) -> float | None:
    """Sum of the four six-hour totals that cover a UTC day, or ``None`` if any is missing.

    Keys are the report hours in ``PRECIPITATION_REPORT_HOURS``, where 24 stands for
    the 00 UTC report of the following day. A missing total could hide rain, so a
    partial sum is never returned.
    """
    totals = [six_hour_totals.get(hour) for hour in PRECIPITATION_REPORT_HOURS]
    if any(total is None for total in totals):
        return None
    return sum(total for total in totals if total is not None)


def daily_total(hourly: Sequence[float | None]) -> float | None:
    """Sum of 24 hourly totals, or ``None`` unless every hour is present.

    Used for modelled precipitation, where a missing hour could hide rain.
    """
    if len(hourly) != HOURS_PER_DAY or any(value is None for value in hourly):
        return None
    return sum(value for value in hourly if value is not None)
