"""Add tank water parameter target ranges.

Revision ID: 20260709_0002
Revises: 20260709_0001
Create Date: 2026-07-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0002"
down_revision = "20260709_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tank_parameter_targets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=40), nullable=False),
        sa.Column("min_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("max_value", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tank_id", "metric_key", name="uq_tank_parameter_target_metric"),
    )
    op.create_index(
        op.f("ix_tank_parameter_targets_metric_key"),
        "tank_parameter_targets",
        ["metric_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tank_parameter_targets_tank_id"),
        "tank_parameter_targets",
        ["tank_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tank_parameter_targets_tank_id"), table_name="tank_parameter_targets")
    op.drop_index(
        op.f("ix_tank_parameter_targets_metric_key"),
        table_name="tank_parameter_targets",
    )
    op.drop_table("tank_parameter_targets")
