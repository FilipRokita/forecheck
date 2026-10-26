"""Hypothesis strategies shared by the domain tests."""

from datetime import UTC, date, datetime, timedelta

from hypothesis import strategies as st

from forecheck.domain.entities import Forecast, Observation
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import MAX_LEAD_DAYS, MIN_LEAD_DAYS, ModelId, StationId, Variable

# Whole numbers keep float sums exact, so properties about addition can use ==.
exact = st.integers(min_value=0, max_value=10_000).map(float)
counts = st.integers(min_value=0, max_value=1_000)

error_stats = st.builds(
    ErrorStats,
    n=counts,
    abs_error_sum=exact,
    error_sum=st.integers(min_value=-10_000, max_value=10_000).map(float),
    squared_error_sum=exact,
    hits=counts,
    misses=counts,
    false_alarms=counts,
    correct_negatives=counts,
    brier_sum=exact,
    brier_n=counts,
)

stations = st.sampled_from([StationId("12566"), StationId("12375")])
models = st.sampled_from([ModelId("icon"), ModelId("ecmwf"), ModelId("gfs")])
variables = st.sampled_from(list(Variable))
leads = st.integers(min_value=MIN_LEAD_DAYS, max_value=MAX_LEAD_DAYS)
valid_dates = st.dates(min_value=date(2024, 1, 1), max_value=date(2030, 12, 31))
values = st.floats(min_value=-60, max_value=1100, allow_nan=False, allow_infinity=False)
probabilities = st.one_of(st.none(), st.floats(min_value=0, max_value=1, allow_nan=False))


@st.composite
def forecasts(draw: st.DrawFn, variable: Variable | None = None) -> Forecast:
    valid = draw(valid_dates)
    lead = draw(leads)
    issued = datetime.combine(valid - timedelta(days=lead), datetime.min.time(), UTC) + timedelta(
        hours=draw(st.integers(0, 23))
    )
    return Forecast(
        station_id=draw(stations),
        model=draw(models),
        variable=variable or draw(variables),
        valid_date=valid,
        issued_at=issued,
        value=draw(values),
        probability=draw(probabilities),
    )


def observation_for(forecast: Forecast, value: float) -> Observation:
    return Observation(forecast.station_id, forecast.variable, forecast.valid_date, value)
