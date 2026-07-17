from __future__ import annotations

from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.application.ports.history import (
    CareHistoryEvent,
    CareHistoryPage,
    HistoryMeasurement,
)
from app.infrastructure.db.models import (
    EventModel,
    FertilizerEventDetailModel,
    MaintenanceEventDetailModel,
    TankModel,
)
from app.infrastructure.repositories.feature_flags import (
    filter_plant_care_events,
    plant_care_is_active,
)

_WATER_METRIC_ORDER = {
    "ammonia": 0,
    "nitrite": 1,
    "nitrate": 2,
    "ph": 3,
    "temperature": 4,
    "kh": 5,
    "gh": 6,
    "tds": 7,
}


class SqlAlchemyCareHistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_tank_history(
        self,
        user_id: int,
        tank_id: int,
        *,
        event_types: tuple[str, ...] | None,
        maintenance_type: str | None,
        page: int,
        page_size: int,
        plant_care_mode: str,
    ) -> CareHistoryPage | None:
        tank = self.session.scalar(
            select(TankModel).where(TankModel.id == tank_id, TankModel.user_id == user_id)
        )
        if tank is None:
            return None

        include_plant_care = plant_care_is_active(
            self.session,
            user_id,
            plant_care_mode,
        )
        conditions = [EventModel.user_id == user_id, EventModel.tank_id == tank_id]
        if event_types is not None:
            conditions.append(EventModel.event_type.in_(event_types))

        count_statement = select(func.count()).select_from(EventModel).where(*conditions)
        event_statement = (
            select(EventModel)
            .where(*conditions)
            .options(
                selectinload(EventModel.measurements),
                selectinload(EventModel.maintenance_detail),
                selectinload(EventModel.feeding_detail),
                selectinload(EventModel.fertilizer_detail).selectinload(
                    FertilizerEventDetailModel.product
                ),
                selectinload(EventModel.photo_detail),
            )
        )
        if maintenance_type is not None:
            count_statement = count_statement.join(
                MaintenanceEventDetailModel,
                MaintenanceEventDetailModel.event_id == EventModel.id,
            ).where(MaintenanceEventDetailModel.maintenance_type == maintenance_type)
            event_statement = event_statement.join(
                MaintenanceEventDetailModel,
                MaintenanceEventDetailModel.event_id == EventModel.id,
            ).where(MaintenanceEventDetailModel.maintenance_type == maintenance_type)

        count_statement = filter_plant_care_events(count_statement, include_plant_care)
        event_statement = filter_plant_care_events(event_statement, include_plant_care)
        total_count = int(self.session.scalar(count_statement) or 0)
        total_pages = max(1, ceil(total_count / page_size))
        current_page = min(page, total_pages)
        event_statement = (
            event_statement.order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        events = [self._history_event(event) for event in self.session.scalars(event_statement)]
        return CareHistoryPage(
            tank_id=tank.id,
            tank_name=tank.name,
            events=events,
            page=current_page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    @staticmethod
    def _history_event(event: EventModel) -> CareHistoryEvent:
        maintenance = event.maintenance_detail
        feeding = event.feeding_detail
        dose = event.fertilizer_detail
        photo = event.photo_detail
        return CareHistoryEvent(
            id=event.id,
            event_type=event.event_type,
            title=event.title,
            occurred_at=event.occurred_at,
            notes=event.notes,
            metadata=dict(event.metadata_json or {}),
            measurements=tuple(
                HistoryMeasurement(
                    metric_key=measurement.metric_key,
                    value=measurement.value,
                    unit=measurement.unit,
                )
                for measurement in sorted(
                    event.measurements,
                    key=lambda item: _WATER_METRIC_ORDER.get(item.metric_key, 99),
                )
            ),
            maintenance_type=maintenance.maintenance_type if maintenance else None,
            duration_minutes=maintenance.duration_minutes if maintenance else None,
            volume_changed_liters=maintenance.volume_changed_liters if maintenance else None,
            equipment_name=maintenance.equipment_name if maintenance else None,
            feeding_food_name=feeding.food_name if feeding else None,
            feeding_amount=feeding.amount if feeding else None,
            feeding_unit=feeding.unit if feeding else None,
            feeding_target=feeding.target_livestock if feeding else None,
            dose_product_name=dose.product.name if dose and dose.product else None,
            dose_amount=dose.dose_amount if dose else None,
            dose_unit=dose.dose_unit if dose else None,
            dose_location=dose.location if dose else None,
            media_asset_id=photo.media_asset_id if photo else None,
            photo_caption=photo.caption if photo else None,
        )
