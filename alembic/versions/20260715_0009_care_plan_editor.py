"""Add care plan provenance and reminder reconciliation.

Revision ID: 20260715_0009
Revises: 20260715_0008
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260715_0009"
down_revision = "20260715_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tank_maintenance_configs") as batch_op:
        batch_op.add_column(sa.Column("config_key", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("task_label", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column(
                "schedule_mode",
                sa.String(length=20),
                nullable=False,
                server_default="scheduled",
            )
        )
        batch_op.add_column(sa.Column("preferred_weekday", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("start_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "reminders_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "provenance",
                sa.String(length=20),
                nullable=False,
                server_default="legacy",
            )
        )
        batch_op.add_column(sa.Column("profile_key", sa.String(length=40), nullable=True))

    op.execute(
        "UPDATE tank_maintenance_configs "
        "SET config_key = config_type, reminders_enabled = enabled, provenance = 'legacy'"
    )

    with op.batch_alter_table("tank_maintenance_configs") as batch_op:
        batch_op.drop_constraint("uq_tank_maintenance_config_type", type_="unique")
        batch_op.alter_column("config_key", existing_type=sa.String(length=120), nullable=False)
        batch_op.create_unique_constraint(
            "uq_tank_maintenance_config_key",
            ["tank_id", "config_key"],
        )
        batch_op.create_index(
            op.f("ix_tank_maintenance_configs_provenance"),
            ["provenance"],
        )
        batch_op.create_index(
            op.f("ix_tank_maintenance_configs_profile_key"),
            ["profile_key"],
        )

    with op.batch_alter_table("reminders") as batch_op:
        batch_op.add_column(sa.Column("maintenance_config_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("superseded_reason", sa.String(length=240), nullable=True))
        batch_op.create_foreign_key(
            "fk_reminders_maintenance_config_id",
            "tank_maintenance_configs",
            ["maintenance_config_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            op.f("ix_reminders_maintenance_config_id"),
            ["maintenance_config_id"],
        )
        batch_op.create_index(op.f("ix_reminders_superseded_at"), ["superseded_at"])


def downgrade() -> None:
    with op.batch_alter_table("reminders") as batch_op:
        batch_op.drop_index(op.f("ix_reminders_superseded_at"))
        batch_op.drop_index(op.f("ix_reminders_maintenance_config_id"))
        batch_op.drop_constraint("fk_reminders_maintenance_config_id", type_="foreignkey")
        batch_op.drop_column("superseded_reason")
        batch_op.drop_column("superseded_at")
        batch_op.drop_column("maintenance_config_id")

    with op.batch_alter_table("tank_maintenance_configs") as batch_op:
        batch_op.drop_index(op.f("ix_tank_maintenance_configs_profile_key"))
        batch_op.drop_index(op.f("ix_tank_maintenance_configs_provenance"))
        batch_op.drop_constraint("uq_tank_maintenance_config_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_tank_maintenance_config_type",
            ["tank_id", "config_type"],
        )
        batch_op.drop_column("profile_key")
        batch_op.drop_column("provenance")
        batch_op.drop_column("notes")
        batch_op.drop_column("reminders_enabled")
        batch_op.drop_column("start_date")
        batch_op.drop_column("preferred_weekday")
        batch_op.drop_column("schedule_mode")
        batch_op.drop_column("task_label")
        batch_op.drop_column("config_key")
