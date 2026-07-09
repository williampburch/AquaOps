from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

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
    tanks: Mapped[list[TankModel]] = relationship(back_populates="user")
    events: Mapped[list[EventModel]] = relationship(back_populates="user")


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserModel] = relationship(back_populates="sessions")


class TankModel(TimestampMixin, Base):
    __tablename__ = "tanks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tank_type: Mapped[str] = mapped_column(String(80), default="freshwater")
    volume_liters: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    lighting: Mapped[Optional[str]] = mapped_column(String(255))
    filtration: Mapped[Optional[str]] = mapped_column(String(255))
    substrate: Mapped[Optional[str]] = mapped_column(String(255))
    started_on: Mapped[Optional[date]] = mapped_column(Date)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

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
    events: Mapped[list[EventModel]] = relationship(back_populates="tank")


class TankParameterTargetModel(TimestampMixin, Base):
    __tablename__ = "tank_parameter_targets"
    __table_args__ = (
        UniqueConstraint("tank_id", "metric_key", name="uq_tank_parameter_target_metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str] = mapped_column(String(40), index=True)
    min_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    max_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    unit: Mapped[str] = mapped_column(String(24))

    tank: Mapped[TankModel] = relationship(back_populates="parameter_targets")


class LivestockModel(TimestampMixin, Base):
    __tablename__ = "livestock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    common_name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    sex: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acquired_on: Mapped[Optional[date]] = mapped_column(Date)
    retired_on: Mapped[Optional[date]] = mapped_column(Date)

    tank: Mapped[TankModel] = relationship(back_populates="livestock")


class PlantModel(TimestampMixin, Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    common_name: Mapped[str] = mapped_column(String(120))
    species: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    planted_on: Mapped[Optional[date]] = mapped_column(Date)
    removed_on: Mapped[Optional[date]] = mapped_column(Date)

    tank: Mapped[TankModel] = relationship(back_populates="plants")


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
    tank_id: Mapped[int] = mapped_column(
        ForeignKey("tanks.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(180))
    notes: Mapped[Optional[str]] = mapped_column(Text, default="", nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[UserModel] = relationship(back_populates="events")
    tank: Mapped[Optional[TankModel]] = relationship(back_populates="events")
    measurements: Mapped[list[EventMeasurementModel]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    maintenance_detail: Mapped[Optional[MaintenanceEventDetailModel]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    fertilizer_detail: Mapped[Optional[FertilizerEventDetailModel]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    feeding_detail: Mapped[Optional[FeedingEventDetailModel]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    photo_detail: Mapped[Optional[PhotoEventDetailModel]] = relationship(
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
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    volume_changed_liters: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    equipment_name: Mapped[Optional[str]] = mapped_column(String(160))

    event: Mapped[EventModel] = relationship(back_populates="maintenance_detail")


class FertilizerProductModel(TimestampMixin, Base):
    __tablename__ = "fertilizer_products"
    __table_args__ = (
        UniqueConstraint("user_id", "product_key", name="uq_fertilizer_product_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    product_key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))
    default_interval_days: Mapped[Optional[int]] = mapped_column(Integer)
    default_dose_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    default_dose_unit: Mapped[Optional[str]] = mapped_column(String(24))
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
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fertilizer_products.id"))
    dose_amount: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    dose_unit: Mapped[str] = mapped_column(String(24))
    location: Mapped[Optional[str]] = mapped_column(String(180))
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    interval_days_override: Mapped[Optional[int]] = mapped_column(Integer)

    event: Mapped[EventModel] = relationship(back_populates="fertilizer_detail")
    product: Mapped[Optional[FertilizerProductModel]] = relationship(back_populates="events")


class FeedingEventDetailModel(Base):
    __tablename__ = "feeding_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    food_name: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3))
    unit: Mapped[Optional[str]] = mapped_column(String(24))
    target_livestock: Mapped[Optional[str]] = mapped_column(String(160))

    event: Mapped[EventModel] = relationship(back_populates="feeding_detail")


class MediaAssetModel(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(120))
    byte_size: Mapped[Optional[int]] = mapped_column(Integer)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    photo_detail: Mapped[Optional[PhotoEventDetailModel]] = relationship(back_populates="media_asset")


class PhotoEventDetailModel(Base):
    __tablename__ = "photo_event_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id", ondelete="CASCADE"))
    caption: Mapped[Optional[str]] = mapped_column(String(240))

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
    tank_id: Optional[Mapped[int]] = mapped_column(
        ForeignKey("tanks.id", ondelete="SET NULL"),
        index=True,
    )
    source_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    reminder_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    source_event: Mapped[Optional[EventModel]] = relationship(back_populates="reminders")
