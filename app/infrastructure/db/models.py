from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.infrastructure.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    preferences: Mapped[UserPreferenceModel | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tanks: Mapped[list[TankModel]] = relationship(back_populates="user")
    events: Mapped[list[EventModel]] = relationship(back_populates="user")


class UserPreferenceModel(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    unit_system: Mapped[str] = mapped_column(String(20), default="us")
    volume_unit: Mapped[str] = mapped_column(String(20), default="gallon")
    temperature_unit: Mapped[str] = mapped_column(String(8), default="F")
    date_format: Mapped[str] = mapped_column(String(20), default="mdy")
    dashboard_density: Mapped[str] = mapped_column(String(20), default="comfortable")
    advanced_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_window_days: Mapped[int] = mapped_column(Integer, default=14)
    enable_livestock: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_plants: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_reports: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_advanced_water: Mapped[bool] = mapped_column(Boolean, default=True)
    plant_care_mode: Mapped[str] = mapped_column(String(20), default="auto")

    user: Mapped[UserModel] = relationship(back_populates="preferences")


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel] = relationship(back_populates="sessions")


class TankModel(TimestampMixin, Base):
    __tablename__ = "tanks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    tank_type: Mapped[str] = mapped_column(String(80), default="freshwater")
    care_profile: Mapped[str] = mapped_column(String(40), default="custom")
    volume_liters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    lighting: Mapped[str | None] = mapped_column(String(255))
    filtration: Mapped[str | None] = mapped_column(String(255))
    substrate: Mapped[str | None] = mapped_column(String(255))
    started_on: Mapped[date | None] = mapped_column(Date)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[UserModel] = relationship(back_populates="tanks")
    livestock: Mapped[list[LivestockModel]] = relationship(
        back_populates="tank",
        cascade="all, delete-orphan",
    )
    plants: Mapped[list[PlantModel]] = relationship(
        back_populates="tank",
        cascade="all, delete-orphan",
    )
    parameter_targets: Mapped[list[TankParameterTargetModel]] = relationship(
        back_populates="tank",
        cascade="all, delete-orphan",
    )
    maintenance_configs: Mapped[list[TankMaintenanceConfigModel]] = relationship(
        back_populates="tank",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[EventModel]] = relationship(back_populates="tank")


class TankParameterTargetModel(TimestampMixin, Base):
    __tablename__ = "tank_parameter_targets"
    __table_args__ = (
        UniqueConstraint("tank_id", "metric_key", name="uq_tank_parameter_target_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str] = mapped_column(String(40), index=True)
    min_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    max_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str] = mapped_column(String(24))

    tank: Mapped[TankModel] = relationship(back_populates="parameter_targets")


class TankMaintenanceConfigModel(TimestampMixin, Base):
    __tablename__ = "tank_maintenance_configs"
    __table_args__ = (
        UniqueConstraint("tank_id", "config_type", name="uq_tank_maintenance_config_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    config_type: Mapped[str] = mapped_column(String(80), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    interval_days: Mapped[int | None] = mapped_column(Integer)

    tank: Mapped[TankModel] = relationship(back_populates="maintenance_configs")


class SpeciesCatalogModel(TimestampMixin, Base):
    __tablename__ = "species_catalog"
    __table_args__ = (
        UniqueConstraint("category", "scientific_name", name="uq_species_catalog_category_species"),
        Index("ix_species_catalog_category_common", "category", "common_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    common_name: Mapped[str] = mapped_column(String(120), index=True)
    scientific_name: Mapped[str | None] = mapped_column(String(160), index=True)
    family: Mapped[str | None] = mapped_column(String(120))
    care_level: Mapped[str | None] = mapped_column(String(40))
    temperament: Mapped[str | None] = mapped_column(String(80))
    min_tank_liters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    temperature_min_f: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    temperature_max_f: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ph_min: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    ph_max: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    social_group_min: Mapped[int | None] = mapped_column(Integer)
    light_requirement: Mapped[str | None] = mapped_column(String(40))
    co2_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    fertilizer_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80), default="builtin")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True)
    external_refs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    aliases: Mapped[list[SpeciesAliasModel]] = relationship(
        back_populates="catalog_entry",
        cascade="all, delete-orphan",
    )
    livestock: Mapped[list[LivestockModel]] = relationship(back_populates="catalog_entry")
    plants: Mapped[list[PlantModel]] = relationship(back_populates="catalog_entry")


class SpeciesAliasModel(Base):
    __tablename__ = "species_aliases"
    __table_args__ = (
        UniqueConstraint("catalog_entry_id", "alias", name="uq_species_alias_entry_alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_entry_id: Mapped[int] = mapped_column(
        ForeignKey("species_catalog.id", ondelete="CASCADE"),
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(160), index=True)
    alias_type: Mapped[str] = mapped_column(String(40), default="common")

    catalog_entry: Mapped[SpeciesCatalogModel] = relationship(back_populates="aliases")


class LivestockModel(TimestampMixin, Base):
    __tablename__ = "livestock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    species_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("species_catalog.id", ondelete="SET NULL"),
        index=True,
    )
    common_name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    sex: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    acquired_on: Mapped[date | None] = mapped_column(Date)
    retired_on: Mapped[date | None] = mapped_column(Date)

    tank: Mapped[TankModel] = relationship(back_populates="livestock")
    catalog_entry: Mapped[SpeciesCatalogModel | None] = relationship(back_populates="livestock")


class PlantModel(TimestampMixin, Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    species_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("species_catalog.id", ondelete="SET NULL"),
        index=True,
    )
    common_name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    planted_on: Mapped[date | None] = mapped_column(Date)
    removed_on: Mapped[date | None] = mapped_column(Date)

    tank: Mapped[TankModel] = relationship(back_populates="plants")
    catalog_entry: Mapped[SpeciesCatalogModel | None] = relationship(back_populates="plants")


class EventModel(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_user_tank_occurred", "user_id", "tank_id", "occurred_at"),
        Index("ix_events_type_occurred", "event_type", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    tank_id: Mapped[int | None] = mapped_column(
        ForeignKey("tanks.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text, default="", nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[UserModel] = relationship(back_populates="events")
    tank: Mapped[TankModel | None] = relationship(back_populates="events")
    measurements: Mapped[list[EventMeasurementModel]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    maintenance_detail: Mapped[MaintenanceEventDetailModel | None] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    fertilizer_detail: Mapped[FertilizerEventDetailModel | None] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    feeding_detail: Mapped[FeedingEventDetailModel | None] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    photo_detail: Mapped[PhotoEventDetailModel | None] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[list[ReminderModel]] = relationship(
        back_populates="source_event",
        cascade="all, delete-orphan",
    )


class EventMeasurementModel(Base):
    __tablename__ = "event_measurements"
    __table_args__ = (UniqueConstraint("event_id", "metric_key", name="uq_event_metric"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    unit: Mapped[str] = mapped_column(String(24))

    event: Mapped[EventModel] = relationship(back_populates="measurements")


class MaintenanceEventDetailModel(Base):
    __tablename__ = "maintenance_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    maintenance_type: Mapped[str] = mapped_column(String(80), index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    volume_changed_liters: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    equipment_name: Mapped[str | None] = mapped_column(String(160))

    event: Mapped[EventModel] = relationship(back_populates="maintenance_detail")


class FertilizerProductModel(TimestampMixin, Base):
    __tablename__ = "fertilizer_products"
    __table_args__ = (
        UniqueConstraint("user_id", "product_key", name="uq_fertilizer_product_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    product_key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))
    default_interval_days: Mapped[int | None] = mapped_column(Integer)
    default_dose_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    default_dose_unit: Mapped[str | None] = mapped_column(String(24))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    events: Mapped[list[FertilizerEventDetailModel]] = relationship(back_populates="product")


class FertilizerEventDetailModel(Base):
    __tablename__ = "fertilizer_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("fertilizer_products.id"))
    dose_amount: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    dose_unit: Mapped[str] = mapped_column(String(24))
    location: Mapped[str | None] = mapped_column(String(180))
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    interval_days_override: Mapped[int | None] = mapped_column(Integer)

    event: Mapped[EventModel] = relationship(back_populates="fertilizer_detail")
    product: Mapped[FertilizerProductModel | None] = relationship(back_populates="events")


class FeedingEventDetailModel(Base):
    __tablename__ = "feeding_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    food_name: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(24))
    target_livestock: Mapped[str | None] = mapped_column(String(160))

    event: Mapped[EventModel] = relationship(back_populates="feeding_detail")


class MediaAssetModel(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(120))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    photo_detail: Mapped[PhotoEventDetailModel | None] = relationship(back_populates="media_asset")


class PhotoEventDetailModel(Base):
    __tablename__ = "photo_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id", ondelete="CASCADE"))
    caption: Mapped[str | None] = mapped_column(String(240))

    event: Mapped[EventModel] = relationship(back_populates="photo_detail")
    media_asset: Mapped[MediaAssetModel] = relationship(back_populates="photo_detail")


class ReminderModel(Base):
    __tablename__ = "reminders"
    __table_args__ = (Index("ix_reminders_user_due", "user_id", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    tank_id: Mapped[int | None] = mapped_column(
        ForeignKey("tanks.id", ondelete="SET NULL"),
        index=True,
    )
    source_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    reminder_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    source_event: Mapped[EventModel | None] = relationship(back_populates="reminders")
