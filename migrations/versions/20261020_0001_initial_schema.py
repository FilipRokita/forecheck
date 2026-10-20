"""Initial schema: forecasts, observations, scores, source state and run log.

Revision ID: 0001
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("station_id", sa.String(16), nullable=False),
        sa.Column("model", sa.String(32), nullable=False),
        sa.Column("variable", sa.String(16), nullable=False),
        sa.Column("valid_date", sa.Date, nullable=False),
        sa.Column("lead_days", sa.SmallInteger, nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(53), nullable=False),
        sa.Column("probability", sa.Float(53)),
        sa.PrimaryKeyConstraint("station_id", "model", "variable", "valid_date", "lead_days"),
        sa.CheckConstraint("lead_days BETWEEN 1 AND 7", name="forecasts_lead_days_range"),
    )
    op.create_index("forecasts_valid_date_idx", "forecasts", ["valid_date"])

    op.create_table(
        "observations",
        sa.Column("station_id", sa.String(16), nullable=False),
        sa.Column("variable", sa.String(16), nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("value", sa.Float(53), nullable=False),
        sa.PrimaryKeyConstraint("station_id", "variable", "day"),
    )

    op.create_table(
        "scores",
        sa.Column("station_id", sa.String(16), nullable=False),
        sa.Column("variable", sa.String(16), nullable=False),
        sa.Column("valid_date", sa.Date, nullable=False),
        sa.Column("model", sa.String(32), nullable=False),
        sa.Column("lead_days", sa.SmallInteger, nullable=False),
        sa.Column("n", sa.Integer, nullable=False),
        sa.Column("abs_error_sum", sa.Float(53), nullable=False),
        sa.Column("error_sum", sa.Float(53), nullable=False),
        sa.Column("squared_error_sum", sa.Float(53), nullable=False),
        sa.Column("hits", sa.Integer, nullable=False),
        sa.Column("misses", sa.Integer, nullable=False),
        sa.Column("false_alarms", sa.Integer, nullable=False),
        sa.Column("correct_negatives", sa.Integer, nullable=False),
        sa.Column("brier_sum", sa.Float(53), nullable=False),
        sa.Column("brier_n", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("station_id", "variable", "valid_date", "model", "lead_days"),
        sa.CheckConstraint("lead_days BETWEEN 1 AND 7", name="scores_lead_days_range"),
    )
    op.create_index("scores_variable_valid_date_idx", "scores", ["variable", "valid_date"])

    op.create_table(
        "source_state",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ok", sa.Boolean, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
    )
    op.create_index("runs_kind_at_idx", "runs", ["kind", "at"])


def downgrade() -> None:
    op.drop_table("runs")
    op.drop_table("source_state")
    op.drop_table("scores")
    op.drop_table("observations")
    op.drop_table("forecasts")
