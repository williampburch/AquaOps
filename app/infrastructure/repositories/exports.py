from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.application.ports.exports import ExportTable
from app.infrastructure.db.models import (
    EventMeasurementModel,
    EventModel,
    FeedingEventDetailModel,
    FertilizerEventDetailModel,
    FertilizerProductModel,
    LivestockModel,
    MaintenanceEventDetailModel,
    MediaAssetModel,
    PhotoEventDetailModel,
    PlantModel,
    ProblemEventLinkModel,
    ProblemModel,
    ReminderModel,
    TankMaintenanceConfigModel,
    TankModel,
    TankParameterTargetModel,
    UserModel,
    UserPreferenceModel,
)


class SqlAlchemyDataExportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_export_tables(self, user_id: int) -> list[ExportTable]:
        return [
            self._table(
                "account.csv",
                ("id", "username", "email", "created_at", "updated_at"),
                select(
                    UserModel.id,
                    UserModel.username,
                    UserModel.email,
                    UserModel.created_at,
                    UserModel.updated_at,
                ).where(UserModel.id == user_id),
            ),
            self._table(
                "preferences.csv",
                (
                    "user_id",
                    "unit_system",
                    "volume_unit",
                    "temperature_unit",
                    "date_format",
                    "dashboard_density",
                    "advanced_mode",
                    "reminder_window_days",
                    "enable_livestock",
                    "enable_plants",
                    "enable_reports",
                    "enable_notifications",
                    "enable_advanced_water",
                    "plant_care_mode",
                ),
                select(
                    UserPreferenceModel.user_id,
                    UserPreferenceModel.unit_system,
                    UserPreferenceModel.volume_unit,
                    UserPreferenceModel.temperature_unit,
                    UserPreferenceModel.date_format,
                    UserPreferenceModel.dashboard_density,
                    UserPreferenceModel.advanced_mode,
                    UserPreferenceModel.reminder_window_days,
                    UserPreferenceModel.enable_livestock,
                    UserPreferenceModel.enable_plants,
                    UserPreferenceModel.enable_reports,
                    UserPreferenceModel.enable_notifications,
                    UserPreferenceModel.enable_advanced_water,
                    UserPreferenceModel.plant_care_mode,
                ).where(UserPreferenceModel.user_id == user_id),
            ),
            self._table(
                "tanks.csv",
                (
                    "id",
                    "name",
                    "tank_type",
                    "care_profile",
                    "volume_liters",
                    "started_on",
                    "description",
                    "lighting",
                    "filtration",
                    "substrate",
                    "archived_at",
                    "created_at",
                    "updated_at",
                ),
                select(
                    TankModel.id,
                    TankModel.name,
                    TankModel.tank_type,
                    TankModel.care_profile,
                    TankModel.volume_liters,
                    TankModel.started_on,
                    TankModel.description,
                    TankModel.lighting,
                    TankModel.filtration,
                    TankModel.substrate,
                    TankModel.archived_at,
                    TankModel.created_at,
                    TankModel.updated_at,
                )
                .where(TankModel.user_id == user_id)
                .order_by(TankModel.id),
            ),
            self._tank_child_table(
                user_id,
                "parameter_targets.csv",
                ("id", "tank_id", "metric_key", "min_value", "max_value", "unit"),
                select(
                    TankParameterTargetModel.id,
                    TankParameterTargetModel.tank_id,
                    TankParameterTargetModel.metric_key,
                    TankParameterTargetModel.min_value,
                    TankParameterTargetModel.max_value,
                    TankParameterTargetModel.unit,
                ),
                TankParameterTargetModel.tank_id,
            ),
            self._tank_child_table(
                user_id,
                "maintenance_schedules.csv",
                ("id", "tank_id", "config_type", "enabled", "interval_days"),
                select(
                    TankMaintenanceConfigModel.id,
                    TankMaintenanceConfigModel.tank_id,
                    TankMaintenanceConfigModel.config_type,
                    TankMaintenanceConfigModel.enabled,
                    TankMaintenanceConfigModel.interval_days,
                ),
                TankMaintenanceConfigModel.tank_id,
            ),
            self._tank_child_table(
                user_id,
                "livestock.csv",
                (
                    "id",
                    "tank_id",
                    "species_catalog_id",
                    "common_name",
                    "species",
                    "quantity",
                    "sex",
                    "notes",
                    "acquired_on",
                    "retired_on",
                    "created_at",
                    "updated_at",
                ),
                select(
                    LivestockModel.id,
                    LivestockModel.tank_id,
                    LivestockModel.species_catalog_id,
                    LivestockModel.common_name,
                    LivestockModel.species,
                    LivestockModel.quantity,
                    LivestockModel.sex,
                    LivestockModel.notes,
                    LivestockModel.acquired_on,
                    LivestockModel.retired_on,
                    LivestockModel.created_at,
                    LivestockModel.updated_at,
                ),
                LivestockModel.tank_id,
            ),
            self._tank_child_table(
                user_id,
                "plants.csv",
                (
                    "id",
                    "tank_id",
                    "species_catalog_id",
                    "common_name",
                    "species",
                    "quantity",
                    "notes",
                    "planted_on",
                    "removed_on",
                    "created_at",
                    "updated_at",
                ),
                select(
                    PlantModel.id,
                    PlantModel.tank_id,
                    PlantModel.species_catalog_id,
                    PlantModel.common_name,
                    PlantModel.species,
                    PlantModel.quantity,
                    PlantModel.notes,
                    PlantModel.planted_on,
                    PlantModel.removed_on,
                    PlantModel.created_at,
                    PlantModel.updated_at,
                ),
                PlantModel.tank_id,
            ),
            self._table(
                "problems.csv",
                (
                    "id",
                    "tank_id",
                    "problem_type",
                    "title",
                    "description",
                    "severity",
                    "status",
                    "started_at",
                    "resolved_at",
                    "resolution_notes",
                    "created_at",
                    "updated_at",
                ),
                select(
                    ProblemModel.id,
                    ProblemModel.tank_id,
                    ProblemModel.problem_type,
                    ProblemModel.title,
                    ProblemModel.description,
                    ProblemModel.severity,
                    ProblemModel.status,
                    ProblemModel.started_at,
                    ProblemModel.resolved_at,
                    ProblemModel.resolution_notes,
                    ProblemModel.created_at,
                    ProblemModel.updated_at,
                )
                .where(ProblemModel.user_id == user_id)
                .order_by(ProblemModel.started_at, ProblemModel.id),
            ),
            self._table(
                "problem_event_links.csv",
                ("id", "problem_id", "event_id", "created_at"),
                select(
                    ProblemEventLinkModel.id,
                    ProblemEventLinkModel.problem_id,
                    ProblemEventLinkModel.event_id,
                    ProblemEventLinkModel.created_at,
                )
                .join(ProblemModel, ProblemModel.id == ProblemEventLinkModel.problem_id)
                .where(ProblemModel.user_id == user_id)
                .order_by(ProblemEventLinkModel.id),
            ),
            self._table(
                "events.csv",
                (
                    "id",
                    "tank_id",
                    "event_type",
                    "title",
                    "notes",
                    "occurred_at",
                    "metadata_json",
                    "created_at",
                    "updated_at",
                ),
                select(
                    EventModel.id,
                    EventModel.tank_id,
                    EventModel.event_type,
                    EventModel.title,
                    EventModel.notes,
                    EventModel.occurred_at,
                    EventModel.metadata_json,
                    EventModel.created_at,
                    EventModel.updated_at,
                )
                .where(EventModel.user_id == user_id)
                .order_by(EventModel.occurred_at, EventModel.id),
            ),
            self._event_detail_table(
                user_id,
                "water_measurements.csv",
                ("id", "event_id", "metric_key", "value", "unit"),
                select(
                    EventMeasurementModel.id,
                    EventMeasurementModel.event_id,
                    EventMeasurementModel.metric_key,
                    EventMeasurementModel.value,
                    EventMeasurementModel.unit,
                ),
                EventMeasurementModel.event_id,
            ),
            self._event_detail_table(
                user_id,
                "maintenance_details.csv",
                (
                    "id",
                    "event_id",
                    "maintenance_type",
                    "duration_minutes",
                    "volume_changed_liters",
                    "equipment_name",
                ),
                select(
                    MaintenanceEventDetailModel.id,
                    MaintenanceEventDetailModel.event_id,
                    MaintenanceEventDetailModel.maintenance_type,
                    MaintenanceEventDetailModel.duration_minutes,
                    MaintenanceEventDetailModel.volume_changed_liters,
                    MaintenanceEventDetailModel.equipment_name,
                ),
                MaintenanceEventDetailModel.event_id,
            ),
            self._event_detail_table(
                user_id,
                "feeding_details.csv",
                ("id", "event_id", "food_name", "amount", "unit", "target_livestock"),
                select(
                    FeedingEventDetailModel.id,
                    FeedingEventDetailModel.event_id,
                    FeedingEventDetailModel.food_name,
                    FeedingEventDetailModel.amount,
                    FeedingEventDetailModel.unit,
                    FeedingEventDetailModel.target_livestock,
                ),
                FeedingEventDetailModel.event_id,
            ),
            self._table(
                "fertilizer_products.csv",
                (
                    "id",
                    "product_key",
                    "name",
                    "default_interval_days",
                    "default_dose_amount",
                    "default_dose_unit",
                    "is_builtin",
                    "created_at",
                    "updated_at",
                ),
                select(
                    FertilizerProductModel.id,
                    FertilizerProductModel.product_key,
                    FertilizerProductModel.name,
                    FertilizerProductModel.default_interval_days,
                    FertilizerProductModel.default_dose_amount,
                    FertilizerProductModel.default_dose_unit,
                    FertilizerProductModel.is_builtin,
                    FertilizerProductModel.created_at,
                    FertilizerProductModel.updated_at,
                )
                .where(FertilizerProductModel.user_id == user_id)
                .order_by(FertilizerProductModel.id),
            ),
            self._table(
                "fertilizer_details.csv",
                (
                    "id",
                    "event_id",
                    "product_id",
                    "product_name",
                    "dose_amount",
                    "dose_unit",
                    "location",
                    "next_due_at",
                    "interval_days_override",
                ),
                select(
                    FertilizerEventDetailModel.id,
                    FertilizerEventDetailModel.event_id,
                    FertilizerEventDetailModel.product_id,
                    FertilizerProductModel.name,
                    FertilizerEventDetailModel.dose_amount,
                    FertilizerEventDetailModel.dose_unit,
                    FertilizerEventDetailModel.location,
                    FertilizerEventDetailModel.next_due_at,
                    FertilizerEventDetailModel.interval_days_override,
                )
                .join(EventModel, EventModel.id == FertilizerEventDetailModel.event_id)
                .outerjoin(
                    FertilizerProductModel,
                    FertilizerProductModel.id == FertilizerEventDetailModel.product_id,
                )
                .where(EventModel.user_id == user_id)
                .order_by(FertilizerEventDetailModel.id),
            ),
            self._table(
                "reminders.csv",
                (
                    "id",
                    "tank_id",
                    "source_event_id",
                    "reminder_type",
                    "title",
                    "due_at",
                    "completed_at",
                    "snoozed_until",
                    "created_at",
                ),
                select(
                    ReminderModel.id,
                    ReminderModel.tank_id,
                    ReminderModel.source_event_id,
                    ReminderModel.reminder_type,
                    ReminderModel.title,
                    ReminderModel.due_at,
                    ReminderModel.completed_at,
                    ReminderModel.snoozed_until,
                    ReminderModel.created_at,
                )
                .where(ReminderModel.user_id == user_id)
                .order_by(ReminderModel.id),
            ),
            self._table(
                "photo_metadata.csv",
                (
                    "event_id",
                    "media_asset_id",
                    "caption",
                    "storage_path",
                    "original_filename",
                    "content_type",
                    "byte_size",
                    "checksum_sha256",
                    "created_at",
                ),
                select(
                    PhotoEventDetailModel.event_id,
                    PhotoEventDetailModel.media_asset_id,
                    PhotoEventDetailModel.caption,
                    MediaAssetModel.storage_path,
                    MediaAssetModel.original_filename,
                    MediaAssetModel.content_type,
                    MediaAssetModel.byte_size,
                    MediaAssetModel.checksum_sha256,
                    MediaAssetModel.created_at,
                )
                .join(EventModel, EventModel.id == PhotoEventDetailModel.event_id)
                .join(MediaAssetModel, MediaAssetModel.id == PhotoEventDetailModel.media_asset_id)
                .where(EventModel.user_id == user_id)
                .order_by(PhotoEventDetailModel.id),
            ),
        ]

    def _tank_child_table(
        self,
        user_id: int,
        filename: str,
        columns: tuple[str, ...],
        statement: Select,
        tank_id_column,
    ) -> ExportTable:
        return self._table(
            filename,
            columns,
            statement.join(TankModel, TankModel.id == tank_id_column)
            .where(TankModel.user_id == user_id)
            .order_by(tank_id_column),
        )

    def _event_detail_table(
        self,
        user_id: int,
        filename: str,
        columns: tuple[str, ...],
        statement: Select,
        event_id_column,
    ) -> ExportTable:
        return self._table(
            filename,
            columns,
            statement.join(EventModel, EventModel.id == event_id_column)
            .where(EventModel.user_id == user_id)
            .order_by(event_id_column),
        )

    def _table(
        self,
        filename: str,
        columns: tuple[str, ...],
        statement: Select,
    ) -> ExportTable:
        rows = [tuple(row) for row in self.session.execute(statement).all()]
        return ExportTable(filename=filename, columns=columns, rows=rows)
