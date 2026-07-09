from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.ports.inventory import (
    InventoryGroup,
    InventorySnapshot,
    InventorySummary,
)
from app.infrastructure.db.models import LivestockModel, PlantModel, TankModel


class SqlAlchemyInventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_livestock(self, user_id: int) -> InventorySnapshot:
        quantity_expression = LivestockModel.quantity
        return self._build_snapshot(
            user_id=user_id,
            model=LivestockModel,
            quantity_expression=quantity_expression,
            inactive_column=LivestockModel.retired_on,
        )

    def get_plants(self, user_id: int) -> InventorySnapshot:
        quantity_expression = func.coalesce(PlantModel.quantity, 1)
        return self._build_snapshot(
            user_id=user_id,
            model=PlantModel,
            quantity_expression=quantity_expression,
            inactive_column=PlantModel.removed_on,
        )

    def _build_snapshot(
        self,
        *,
        user_id: int,
        model: type[LivestockModel] | type[PlantModel],
        quantity_expression,
        inactive_column,
    ) -> InventorySnapshot:
        base_filters = (TankModel.user_id == user_id, inactive_column.is_(None))
        summary = InventorySummary(
            total_count=self._total_count(model, quantity_expression, base_filters),
            species_count=self._species_count(model, base_filters),
            tank_count=self._tank_count(model, base_filters),
        )
        return InventorySnapshot(
            summary=summary,
            groups=self._groups(model, quantity_expression, base_filters),
        )

    def _total_count(self, model, quantity_expression, base_filters) -> int:
        statement = (
            select(func.coalesce(func.sum(quantity_expression), 0))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _species_count(self, model, base_filters) -> int:
        species_key = func.coalesce(model.species, model.common_name)
        statement = (
            select(func.count(func.distinct(species_key)))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _tank_count(self, model, base_filters) -> int:
        statement = (
            select(func.count(func.distinct(model.tank_id)))
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
        )
        return int(self.session.scalar(statement) or 0)

    def _groups(self, model, quantity_expression, base_filters) -> list[InventoryGroup]:
        statement = (
            select(
                model.common_name,
                model.species,
                func.sum(quantity_expression),
                func.group_concat(func.distinct(TankModel.name)),
            )
            .select_from(model)
            .join(TankModel, TankModel.id == model.tank_id)
            .where(*base_filters)
            .group_by(model.common_name, model.species)
            .order_by(func.sum(quantity_expression).desc(), model.common_name.asc())
        )
        return [
            InventoryGroup(
                common_name=common_name,
                species=species,
                quantity=int(quantity or 0),
                tank_names=self._split_tank_names(tank_names),
            )
            for common_name, species, quantity, tank_names in self.session.execute(statement).all()
        ]

    def _split_tank_names(self, tank_names: str | None) -> list[str]:
        if not tank_names:
            return []
        return sorted(tank_names.split(","))
