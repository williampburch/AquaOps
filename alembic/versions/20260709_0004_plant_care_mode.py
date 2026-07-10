"""Add plant care mode preference.

Revision ID: 20260709_0004
Revises: 20260709_0003
Create Date: 2026-07-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0004"
down_revision = "20260709_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "plant_care_mode",
            sa.String(length=20),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "plant_care_mode")
