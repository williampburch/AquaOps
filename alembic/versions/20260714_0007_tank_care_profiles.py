"""Add tank care profiles.

Revision ID: 20260714_0007
Revises: 20260710_0006
Create Date: 2026-07-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260714_0007"
down_revision = "20260710_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tanks",
        sa.Column(
            "care_profile",
            sa.String(length=40),
            nullable=False,
            server_default="custom",
        ),
    )


def downgrade() -> None:
    op.drop_column("tanks", "care_profile")
