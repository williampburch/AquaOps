"""Initial AquaOps schema.

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "fertilizer_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("product_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("default_interval_days", sa.Integer(), nullable=True),
        sa.Column("default_dose_amount", sa.Numeric(10, 3), nullable=True),
        sa.Column("default_dose_unit", sa.String(length=24), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_key", name="uq_fertilizer_product_user_key"),
    )
    op.create_index(
        op.f("ix_fertilizer_products_product_key"),
        "fertilizer_products",
        ["product_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fertilizer_products_user_id"),
        "fertilizer_products",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_assets_checksum_sha256"), "media_assets", ["checksum_sha256"])
    op.create_index(op.f("ix_media_assets_user_id"), "media_assets", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"])
    op.create_index(op.f("ix_sessions_token_hash"), "sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"])

    op.create_table(
        "tanks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tank_type", sa.String(length=80), nullable=False),
        sa.Column("volume_liters", sa.Numeric(8, 2), nullable=True),
        sa.Column("lighting", sa.String(length=255), nullable=True),
        sa.Column("filtration", sa.String(length=255), nullable=True),
        sa.Column("substrate", sa.String(length=255), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tanks_archived_at"), "tanks", ["archived_at"])
    op.create_index(op.f("ix_tanks_user_id"), "tanks", ["user_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"])
    op.create_index(op.f("ix_events_occurred_at"), "events", ["occurred_at"])
    op.create_index(op.f("ix_events_tank_id"), "events", ["tank_id"])
    op.create_index("ix_events_type_occurred", "events", ["event_type", "occurred_at"])
    op.create_index(op.f("ix_events_user_id"), "events", ["user_id"])
    op.create_index("ix_events_user_tank_occurred", "events", ["user_id", "tank_id", "occurred_at"])

    op.create_table(
        "livestock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("common_name", sa.String(length=120), nullable=False),
        sa.Column("species", sa.String(length=160), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("acquired_on", sa.Date(), nullable=True),
        sa.Column("retired_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_livestock_tank_id"), "livestock", ["tank_id"])

    op.create_table(
        "plants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("common_name", sa.String(length=120), nullable=False),
        sa.Column("species", sa.String(length=160), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("planted_on", sa.Date(), nullable=True),
        sa.Column("removed_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plants_tank_id"), "plants", ["tank_id"])

    op.create_table(
        "event_measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "metric_key", name="uq_event_metric"),
    )
    op.create_index(op.f("ix_event_measurements_event_id"), "event_measurements", ["event_id"])
    op.create_index(op.f("ix_event_measurements_metric_key"), "event_measurements", ["metric_key"])

    op.create_table(
        "feeding_event_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("food_name", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=True),
        sa.Column("target_livestock", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feeding_event_details_event_id"),
        "feeding_event_details",
        ["event_id"],
        unique=True,
    )

    op.create_table(
        "fertilizer_event_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("dose_amount", sa.Numeric(10, 3), nullable=False),
        sa.Column("dose_unit", sa.String(length=24), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_days_override", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["fertilizer_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fertilizer_event_details_event_id"),
        "fertilizer_event_details",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_fertilizer_event_details_next_due_at"), "fertilizer_event_details", ["next_due_at"]
    )

    op.create_table(
        "maintenance_event_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("maintenance_type", sa.String(length=80), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("volume_changed_liters", sa.Numeric(8, 2), nullable=True),
        sa.Column("equipment_name", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_maintenance_event_details_event_id"),
        "maintenance_event_details",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_maintenance_event_details_maintenance_type"),
        "maintenance_event_details",
        ["maintenance_type"],
    )

    op.create_table(
        "photo_event_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("media_asset_id", sa.Integer(), nullable=False),
        sa.Column("caption", sa.String(length=240), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_photo_event_details_event_id"), "photo_event_details", ["event_id"], unique=True
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=True),
        sa.Column("source_event_id", sa.Integer(), nullable=True),
        sa.Column("reminder_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reminders_completed_at"), "reminders", ["completed_at"])
    op.create_index(op.f("ix_reminders_due_at"), "reminders", ["due_at"])
    op.create_index(op.f("ix_reminders_reminder_type"), "reminders", ["reminder_type"])
    op.create_index(op.f("ix_reminders_tank_id"), "reminders", ["tank_id"])
    op.create_index(op.f("ix_reminders_user_id"), "reminders", ["user_id"])
    op.create_index("ix_reminders_user_due", "reminders", ["user_id", "due_at"])


def downgrade() -> None:
    op.drop_index("ix_reminders_user_due", table_name="reminders")
    op.drop_index(op.f("ix_reminders_user_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_tank_id"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_reminder_type"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_due_at"), table_name="reminders")
    op.drop_index(op.f("ix_reminders_completed_at"), table_name="reminders")
    op.drop_table("reminders")
    op.drop_index(op.f("ix_photo_event_details_event_id"), table_name="photo_event_details")
    op.drop_table("photo_event_details")
    op.drop_index(
        op.f("ix_maintenance_event_details_maintenance_type"),
        table_name="maintenance_event_details",
    )
    op.drop_index(
        op.f("ix_maintenance_event_details_event_id"), table_name="maintenance_event_details"
    )
    op.drop_table("maintenance_event_details")
    op.drop_index(
        op.f("ix_fertilizer_event_details_next_due_at"), table_name="fertilizer_event_details"
    )
    op.drop_index(
        op.f("ix_fertilizer_event_details_event_id"), table_name="fertilizer_event_details"
    )
    op.drop_table("fertilizer_event_details")
    op.drop_index(op.f("ix_feeding_event_details_event_id"), table_name="feeding_event_details")
    op.drop_table("feeding_event_details")
    op.drop_index(op.f("ix_event_measurements_metric_key"), table_name="event_measurements")
    op.drop_index(op.f("ix_event_measurements_event_id"), table_name="event_measurements")
    op.drop_table("event_measurements")
    op.drop_index(op.f("ix_plants_tank_id"), table_name="plants")
    op.drop_table("plants")
    op.drop_index(op.f("ix_livestock_tank_id"), table_name="livestock")
    op.drop_table("livestock")
    op.drop_index("ix_events_user_tank_occurred", table_name="events")
    op.drop_index(op.f("ix_events_user_id"), table_name="events")
    op.drop_index("ix_events_type_occurred", table_name="events")
    op.drop_index(op.f("ix_events_tank_id"), table_name="events")
    op.drop_index(op.f("ix_events_occurred_at"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_tanks_user_id"), table_name="tanks")
    op.drop_index(op.f("ix_tanks_archived_at"), table_name="tanks")
    op.drop_table("tanks")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_token_hash"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_media_assets_user_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_checksum_sha256"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index(op.f("ix_fertilizer_products_user_id"), table_name="fertilizer_products")
    op.drop_index(op.f("ix_fertilizer_products_product_key"), table_name="fertilizer_products")
    op.drop_table("fertilizer_products")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
