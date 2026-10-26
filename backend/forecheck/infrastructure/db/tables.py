"""The database schema. ``migrations/`` creates the same tables; a test compares the two."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Table,
    Text,
)

metadata = MetaData()

# Forecasts wait here until their day has been measured, then they are scored and removed.
forecasts = Table(
    "forecasts",
    metadata,
    Column("station_id", String(16), nullable=False),
    Column("model", String(32), nullable=False),
    Column("variable", String(16), nullable=False),
    Column("valid_date", Date, nullable=False),
    Column("lead_days", SmallInteger, nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("value", Float(53), nullable=False),
    Column("probability", Float(53)),
    PrimaryKeyConstraint("station_id", "model", "variable", "valid_date", "lead_days"),
    CheckConstraint("lead_days BETWEEN 1 AND 7", name="forecasts_lead_days_range"),
    Index("forecasts_valid_date_idx", "valid_date"),
)

# One figure per station, variable and UTC day: the ground truth.
observations = Table(
    "observations",
    metadata,
    Column("station_id", String(16), nullable=False),
    Column("variable", String(16), nullable=False),
    Column("day", Date, nullable=False),
    Column("value", Float(53), nullable=False),
    PrimaryKeyConstraint("station_id", "variable", "day"),
)

# Summable statistics of scored forecasts. Rankings over any period are sums of these rows.
scores = Table(
    "scores",
    metadata,
    Column("station_id", String(16), nullable=False),
    Column("variable", String(16), nullable=False),
    Column("valid_date", Date, nullable=False),
    Column("model", String(32), nullable=False),
    Column("lead_days", SmallInteger, nullable=False),
    Column("n", Integer, nullable=False),
    Column("abs_error_sum", Float(53), nullable=False),
    Column("error_sum", Float(53), nullable=False),
    Column("squared_error_sum", Float(53), nullable=False),
    Column("hits", Integer, nullable=False),
    Column("misses", Integer, nullable=False),
    Column("false_alarms", Integer, nullable=False),
    Column("correct_negatives", Integer, nullable=False),
    Column("brier_sum", Float(53), nullable=False),
    Column("brier_n", Integer, nullable=False),
    PrimaryKeyConstraint("station_id", "variable", "valid_date", "model", "lead_days"),
    CheckConstraint("lead_days BETWEEN 1 AND 7", name="scores_lead_days_range"),
    Index("scores_variable_valid_date_idx", "variable", "valid_date"),
)

# What the app remembers between runs, for example which archive versions it has read.
source_state = Table(
    "source_state",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("value", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# One row per step of each scheduled run, to tell a visitor how fresh the data is.
runs = Table(
    "runs",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("kind", String(16), nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("ok", Boolean, nullable=False),
    Column("message", Text, nullable=False),
    Index("runs_kind_at_idx", "kind", "at"),
)
