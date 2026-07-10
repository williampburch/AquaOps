"""Add user preferences.

Revision ID: 20260709_0003
Revises: 20260709_0002
Create Date: 2026-07-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0003"
down_revision = "20260709_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("unit_system", sa.String(length=20), nullable=False),
        sa.Column("volume_unit", sa.String(length=20), nullable=False),
        sa.Column("temperature_unit", sa.String(length=8), nullable=False),
        sa.Column("date_format", sa.String(length=20), nullable=False),
        sa.Column("dashboard_density", sa.String(length=20), nullable=False),
        sa.Column("advanced_mode", sa.Boolean(), nullable=False),
        sa.Column("reminder_window_days", sa.Integer(), nullable=False),
        sa.Column("enable_livestock", sa.Boolean(), nullable=False),
        sa.Column("enable_plants", sa.Boolean(), nullable=False),
        sa.Column("enable_reports", sa.Boolean(), nullable=False),
        sa.Column("enable_notifications", sa.Boolean(), nullable=False),
        sa.Column("enable_advanced_water", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
