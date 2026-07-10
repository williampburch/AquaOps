"""Add tank maintenance configs.

Revision ID: 20260710_0006
Revises: 20260709_0005
Create Date: 2026-07-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260710_0006"
down_revision = "20260709_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tank_maintenance_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("config_type", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tank_id", "config_type", name="uq_tank_maintenance_config_type"),
    )
    op.create_index(
        op.f("ix_tank_maintenance_configs_config_type"),
        "tank_maintenance_configs",
        ["config_type"],
    )
    op.create_index(
        op.f("ix_tank_maintenance_configs_tank_id"),
        "tank_maintenance_configs",
        ["tank_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tank_maintenance_configs_tank_id"),
        table_name="tank_maintenance_configs",
    )
    op.drop_index(
        op.f("ix_tank_maintenance_configs_config_type"),
        table_name="tank_maintenance_configs",
    )
    op.drop_table("tank_maintenance_configs")
