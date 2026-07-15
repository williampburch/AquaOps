"""Add problem tracking and event links.

Revision ID: 20260715_0008
Revises: 20260714_0007
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260715_0008"
down_revision = "20260714_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("problem_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_problems_problem_type"), "problems", ["problem_type"])
    op.create_index(op.f("ix_problems_resolved_at"), "problems", ["resolved_at"])
    op.create_index(op.f("ix_problems_severity"), "problems", ["severity"])
    op.create_index(op.f("ix_problems_started_at"), "problems", ["started_at"])
    op.create_index(op.f("ix_problems_status"), "problems", ["status"])
    op.create_index(op.f("ix_problems_tank_id"), "problems", ["tank_id"])
    op.create_index(op.f("ix_problems_user_id"), "problems", ["user_id"])
    op.create_index(
        "ix_problems_user_status_started",
        "problems",
        ["user_id", "status", "started_at"],
    )

    op.create_table(
        "problem_event_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", "event_id", name="uq_problem_event_link"),
    )
    op.create_index(op.f("ix_problem_event_links_event_id"), "problem_event_links", ["event_id"])
    op.create_index(
        op.f("ix_problem_event_links_problem_id"),
        "problem_event_links",
        ["problem_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_problem_event_links_problem_id"), table_name="problem_event_links")
    op.drop_index(op.f("ix_problem_event_links_event_id"), table_name="problem_event_links")
    op.drop_table("problem_event_links")
    op.drop_index("ix_problems_user_status_started", table_name="problems")
    op.drop_index(op.f("ix_problems_user_id"), table_name="problems")
    op.drop_index(op.f("ix_problems_tank_id"), table_name="problems")
    op.drop_index(op.f("ix_problems_status"), table_name="problems")
    op.drop_index(op.f("ix_problems_started_at"), table_name="problems")
    op.drop_index(op.f("ix_problems_severity"), table_name="problems")
    op.drop_index(op.f("ix_problems_resolved_at"), table_name="problems")
    op.drop_index(op.f("ix_problems_problem_type"), table_name="problems")
    op.drop_table("problems")
