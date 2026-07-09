from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.domain.enums import EventType, MaintenanceType
from app.domain.water import FRESHWATER_BEGINNER_TARGETS
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
    ReminderModel,
    SessionModel,
    TankModel,
    TankParameterTargetModel,
    UserModel,
)

DEMO_EMAIL = "demo@example.com"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo-password"


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    email: str
    password: str
    tank_count: int
    event_count: int
    reminder_count: int


@dataclass(frozen=True, slots=True)
class DemoTankSpec:
    name: str
    description: str
    tank_type: str
    volume_liters: Decimal
    lighting: str
    filtration: str
    substrate: str
    started_days_ago: int
    nitrate_base: float
    ph_base: float
    temp_base: float
    kh: float
    gh: float
    tds_base: float
    livestock: tuple[tuple[str, str, int], ...]
    plants: tuple[tuple[str, str, int], ...]


DEMO_TANKS: tuple[DemoTankSpec, ...] = (
    DemoTankSpec(
        name="River Desk 29G",
        description="A peaceful planted community tank with driftwood and schooling fish.",
        tank_type="planted freshwater",
        volume_liters=Decimal("109.78"),
        lighting="Fluval Plant 3.0, 7 hour photoperiod",
        filtration="Oase Biomaster Thermo 250",
        substrate="Aquasoil cap over root-tab enriched sand",
        started_days_ago=210,
        nitrate_base=12,
        ph_base=7.2,
        temp_base=77.4,
        kh=5,
        gh=8,
        tds_base=182,
        livestock=(
            ("Neon tetra", "Paracheirodon innesi", 14),
            ("Panda cory", "Corydoras panda", 7),
            ("Nerite snail", "Neritina natalensis", 3),
        ),
        plants=(
            ("Amazon sword", "Echinodorus grisebachii", 2),
            ("Java fern", "Microsorum pteropus", 4),
            ("Crypt wendtii", "Cryptocoryne wendtii", 8),
        ),
    ),
    DemoTankSpec(
        name="Shrimp Garden Nano",
        description="Low-tech shrimp tank with moss, botanicals, and slow-growing plants.",
        tank_type="freshwater shrimp",
        volume_liters=Decimal("37.85"),
        lighting="Hygger nano LED, 6 hour photoperiod",
        filtration="Sponge filter",
        substrate="Inert black sand with leaf litter",
        started_days_ago=150,
        nitrate_base=6,
        ph_base=7.0,
        temp_base=73.5,
        kh=4,
        gh=7,
        tds_base=155,
        livestock=(
            ("Cherry shrimp", "Neocaridina davidi", 32),
            ("Ramshorn snail", "Planorbidae", 10),
        ),
        plants=(
            ("Java moss", "Taxiphyllum barbieri", 6),
            ("Anubias nana petite", "Anubias barteri var. nana", 5),
            ("Salvinia", "Salvinia minima", 12),
        ),
    ),
    DemoTankSpec(
        name="Blackwater Corner",
        description="Tannin-stained soft-water setup with leaf litter and floating plants.",
        tank_type="blackwater freshwater",
        volume_liters=Decimal("75.71"),
        lighting="Finnex Stingray, subdued",
        filtration="AquaClear 50 with prefilter sponge",
        substrate="Fine sand, catappa leaves, alder cones",
        started_days_ago=95,
        nitrate_base=9,
        ph_base=6.7,
        temp_base=78.2,
        kh=2,
        gh=5,
        tds_base=118,
        livestock=(
            ("Ember tetra", "Hyphessobrycon amandae", 18),
            ("Honey gourami", "Trichogaster chuna", 2),
        ),
        plants=(
            ("Frogbit", "Limnobium laevigatum", 10),
            ("Water sprite", "Ceratopteris thalictroides", 4),
        ),
    ),
)


def seed_demo_data(
    session: Session,
    settings: Settings,
    *,
    allow_production: bool = False,
) -> DemoSeedResult:
    if settings.is_production and not allow_production:
        raise RuntimeError("Refusing to seed demo data while APP_ENV=production")

    _reset_demo_user(session)
    demo_user = UserModel(
        email=DEMO_EMAIL,
        username=DEMO_USERNAME,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    session.add(demo_user)
    session.flush()

    products = _create_fertilizer_products(session, demo_user.id)
    today = datetime.now(UTC).date()

    event_count = 0
    for index, tank_spec in enumerate(DEMO_TANKS):
        tank = _create_tank(session, demo_user.id, tank_spec, today)
        _seed_targets(session, tank.id, tank_spec)
        _seed_inventory(session, tank.id, tank_spec, today)
        event_count += _seed_water_tests(session, demo_user.id, tank.id, tank_spec, today, index)
        event_count += _seed_maintenance(session, demo_user.id, tank.id, tank_spec, today)
        event_count += _seed_feedings(session, demo_user.id, tank.id, today, index)
        event_count += _seed_fertilizers(session, demo_user.id, tank.id, products, today, index)
        event_count += _seed_observations(session, demo_user.id, tank.id, today, index)
        _seed_reminders(session, demo_user.id, tank.id, today, index)

    session.commit()
    reminder_count = session.scalar(
        select(func.count()).select_from(ReminderModel).where(ReminderModel.user_id == demo_user.id)
    )
    return DemoSeedResult(
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        tank_count=len(DEMO_TANKS),
        event_count=event_count,
        reminder_count=int(reminder_count or 0),
    )


def _reset_demo_user(session: Session) -> None:
    demo_user = session.execute(
        select(UserModel).where(UserModel.email == DEMO_EMAIL)
    ).scalar_one_or_none()
    if demo_user is None:
        return

    tank_ids = list(
        session.scalars(select(TankModel.id).where(TankModel.user_id == demo_user.id)).all()
    )
    event_ids = list(
        session.scalars(select(EventModel.id).where(EventModel.user_id == demo_user.id)).all()
    )

    if event_ids:
        for model in (
            EventMeasurementModel,
            MaintenanceEventDetailModel,
            FertilizerEventDetailModel,
            FeedingEventDetailModel,
            PhotoEventDetailModel,
        ):
            session.execute(delete(model).where(model.event_id.in_(event_ids)))

    session.execute(delete(ReminderModel).where(ReminderModel.user_id == demo_user.id))
    session.execute(delete(SessionModel).where(SessionModel.user_id == demo_user.id))
    session.execute(delete(MediaAssetModel).where(MediaAssetModel.user_id == demo_user.id))
    session.execute(
        delete(FertilizerProductModel).where(FertilizerProductModel.user_id == demo_user.id)
    )
    session.execute(delete(EventModel).where(EventModel.user_id == demo_user.id))

    if tank_ids:
        session.execute(delete(LivestockModel).where(LivestockModel.tank_id.in_(tank_ids)))
        session.execute(delete(PlantModel).where(PlantModel.tank_id.in_(tank_ids)))
        session.execute(
            delete(TankParameterTargetModel).where(TankParameterTargetModel.tank_id.in_(tank_ids))
        )

    session.execute(delete(TankModel).where(TankModel.user_id == demo_user.id))
    session.execute(delete(UserModel).where(UserModel.id == demo_user.id))
    session.flush()


def _create_fertilizer_products(
    session: Session, user_id: int
) -> dict[str, FertilizerProductModel]:
    products = {
        "flourish": FertilizerProductModel(
            user_id=user_id,
            product_key="seachem_flourish",
            name="Seachem Flourish",
            default_interval_days=7,
            default_dose_amount=Decimal("2.5"),
            default_dose_unit="ml",
            is_builtin=True,
        ),
        "root_tabs": FertilizerProductModel(
            user_id=user_id,
            product_key="root_tabs",
            name="Root Tabs",
            default_interval_days=90,
            default_dose_amount=Decimal("3"),
            default_dose_unit="tabs",
            is_builtin=True,
        ),
        "easy_green": FertilizerProductModel(
            user_id=user_id,
            product_key="easy_green",
            name="Easy Green",
            default_interval_days=7,
            default_dose_amount=Decimal("1"),
            default_dose_unit="pump",
            is_builtin=True,
        ),
    }
    session.add_all(products.values())
    session.flush()
    return products


def _create_tank(
    session: Session,
    user_id: int,
    tank_spec: DemoTankSpec,
    today: date,
) -> TankModel:
    tank = TankModel(
        user_id=user_id,
        name=tank_spec.name,
        description=tank_spec.description,
        tank_type=tank_spec.tank_type,
        volume_liters=tank_spec.volume_liters,
        lighting=tank_spec.lighting,
        filtration=tank_spec.filtration,
        substrate=tank_spec.substrate,
        started_on=today - timedelta(days=tank_spec.started_days_ago),
    )
    session.add(tank)
    session.flush()
    return tank


def _seed_targets(session: Session, tank_id: int, tank_spec: DemoTankSpec) -> None:
    for target in FRESHWATER_BEGINNER_TARGETS:
        min_value = target.min_value
        max_value = target.max_value
        if target.metric_key == "ph":
            min_value = _decimal(tank_spec.ph_base - 0.35)
            max_value = _decimal(tank_spec.ph_base + 0.35)
        elif target.metric_key == "temperature":
            min_value = _decimal(tank_spec.temp_base - 2)
            max_value = _decimal(tank_spec.temp_base + 2)
        elif target.metric_key == "nitrate":
            max_value = Decimal("30")

        session.add(
            TankParameterTargetModel(
                tank_id=tank_id,
                metric_key=target.metric_key,
                min_value=min_value,
                max_value=max_value,
                unit=target.unit,
            )
        )


def _seed_inventory(
    session: Session,
    tank_id: int,
    tank_spec: DemoTankSpec,
    today: date,
) -> None:
    for offset, (common_name, species, quantity) in enumerate(tank_spec.livestock):
        session.add(
            LivestockModel(
                tank_id=tank_id,
                common_name=common_name,
                species=species,
                quantity=quantity,
                notes="Healthy demo population",
                acquired_on=today - timedelta(days=tank_spec.started_days_ago - 21 - offset * 8),
            )
        )

    for offset, (common_name, species, quantity) in enumerate(tank_spec.plants):
        session.add(
            PlantModel(
                tank_id=tank_id,
                common_name=common_name,
                species=species,
                quantity=quantity,
                notes="Demo plant mass for tracking growth over time",
                planted_on=today - timedelta(days=tank_spec.started_days_ago - 7 - offset * 5),
            )
        )


def _seed_water_tests(
    session: Session,
    user_id: int,
    tank_id: int,
    tank_spec: DemoTankSpec,
    today: date,
    tank_index: int,
) -> int:
    count = 0
    for sample_index, days_ago in enumerate(range(120, -1, -4)):
        cycle_factor = max(0.0, 1.0 - sample_index / 9)
        nitrate_wave = 4.5 * math.sin((sample_index + tank_index) / 2.8)
        nitrate = max(1.0, tank_spec.nitrate_base + nitrate_wave + (sample_index % 5) * 1.4)
        ammonia = 0.25 * cycle_factor if sample_index < 7 and tank_index == 2 else 0
        nitrite = 0.15 * cycle_factor if sample_index < 8 and tank_index == 2 else 0
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.WATER_TEST.value,
            title="Water test",
            occurred_at=_at(today - timedelta(days=days_ago), hour=8),
            notes="Generated demo reading",
        )
        measurements = {
            "ammonia": (ammonia, "ppm"),
            "nitrite": (nitrite, "ppm"),
            "nitrate": (nitrate, "ppm"),
            "ph": (tank_spec.ph_base + 0.18 * math.sin(sample_index / 3.0), "pH"),
            "temperature": (tank_spec.temp_base + 0.7 * math.sin(sample_index / 4.0), "F"),
            "kh": (tank_spec.kh + 0.3 * math.sin(sample_index / 5.0), "dKH"),
            "gh": (tank_spec.gh + 0.4 * math.sin(sample_index / 4.5), "dGH"),
            "tds": (tank_spec.tds_base + 10 * math.sin(sample_index / 3.5), "ppm"),
        }
        for metric_key, (value, unit) in measurements.items():
            session.add(
                EventMeasurementModel(
                    event_id=event.id,
                    metric_key=metric_key,
                    value=_decimal(value),
                    unit=unit,
                )
            )
        count += 1
    return count


def _seed_maintenance(
    session: Session,
    user_id: int,
    tank_id: int,
    tank_spec: DemoTankSpec,
    today: date,
) -> int:
    count = 0
    for days_ago in range(112, -1, -14):
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.MAINTENANCE.value,
            title="Water change",
            occurred_at=_at(today - timedelta(days=days_ago), hour=10),
            notes="Conditioned and temperature-matched replacement water.",
        )
        session.add(
            MaintenanceEventDetailModel(
                event_id=event.id,
                maintenance_type=MaintenanceType.WATER_CHANGE.value,
                duration_minutes=35,
                volume_changed_liters=_decimal(float(tank_spec.volume_liters) * 0.25),
                equipment_name=None,
            )
        )
        count += 1

    for days_ago in (84, 42, 7):
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.MAINTENANCE.value,
            title="Glass cleaning and plant trim",
            occurred_at=_at(today - timedelta(days=days_ago), hour=11),
            notes="Removed light algae film and trimmed fast growers.",
        )
        session.add(
            MaintenanceEventDetailModel(
                event_id=event.id,
                maintenance_type=MaintenanceType.PLANT_TRIMMING.value,
                duration_minutes=25,
                volume_changed_liters=None,
                equipment_name=None,
            )
        )
        count += 1
    return count


def _seed_feedings(
    session: Session,
    user_id: int,
    tank_id: int,
    today: date,
    tank_index: int,
) -> int:
    foods = ("micro pellets", "frozen brine shrimp", "algae wafer")
    count = 0
    for sequence, days_ago in enumerate(range(45, -1, -2)):
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.FEEDING.value,
            title="Feeding",
            occurred_at=_at(today - timedelta(days=days_ago), hour=18),
            notes=None,
        )
        session.add(
            FeedingEventDetailModel(
                event_id=event.id,
                food_name=foods[(sequence + tank_index) % len(foods)],
                amount=Decimal("1.0"),
                unit="pinch",
                target_livestock="community",
            )
        )
        count += 1
    return count


def _seed_fertilizers(
    session: Session,
    user_id: int,
    tank_id: int,
    products: dict[str, FertilizerProductModel],
    today: date,
    tank_index: int,
) -> int:
    count = 0
    liquid_product = products["easy_green" if tank_index == 0 else "flourish"]
    for days_ago in range(56, -1, -7):
        occurred_at = _at(today - timedelta(days=days_ago), hour=9)
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.FERTILIZER.value,
            title=f"{liquid_product.name} dose",
            occurred_at=occurred_at,
            notes="Demo weekly liquid fertilizer dose.",
        )
        session.add(
            FertilizerEventDetailModel(
                event_id=event.id,
                product_id=liquid_product.id,
                dose_amount=liquid_product.default_dose_amount or Decimal("1"),
                dose_unit=liquid_product.default_dose_unit or "dose",
                location="water column",
                next_due_at=occurred_at + timedelta(days=7),
                interval_days_override=None,
            )
        )
        count += 1

    if tank_index in (0, 1):
        event = _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.FERTILIZER.value,
            title="Root tabs refreshed",
            occurred_at=_at(today - timedelta(days=18), hour=14),
            notes="Placed tabs near heavy root feeders.",
        )
        session.add(
            FertilizerEventDetailModel(
                event_id=event.id,
                product_id=products["root_tabs"].id,
                dose_amount=Decimal("4") if tank_index == 0 else Decimal("2"),
                dose_unit="tabs",
                location="front-left, center sword, rear-right",
                next_due_at=_at(today + timedelta(days=72), hour=9),
                interval_days_override=90,
            )
        )
        count += 1
    return count


def _seed_observations(
    session: Session,
    user_id: int,
    tank_id: int,
    today: date,
    tank_index: int,
) -> int:
    notes = (
        "New crypt leaves visible after last trim.",
        "Water clarity improved after filter floss replacement.",
        "Fish schooling tightly after lights ramped down.",
    )
    for offset, note in enumerate(notes):
        _add_event(
            session,
            user_id=user_id,
            tank_id=tank_id,
            event_type=EventType.NOTE.value,
            title="Observation",
            occurred_at=_at(today - timedelta(days=21 - offset * 6 - tank_index), hour=20),
            notes=note,
        )
    return len(notes)


def _seed_reminders(
    session: Session,
    user_id: int,
    tank_id: int,
    today: date,
    tank_index: int,
) -> None:
    reminders = (
        ("Water change", "maintenance", today + timedelta(days=3 + tank_index)),
        ("Weekly fertilizer dose", "fertilizer", today + timedelta(days=5 + tank_index)),
        ("Review water test trend", "water_test", today + timedelta(days=2)),
    )
    for title, reminder_type, due_on in reminders:
        session.add(
            ReminderModel(
                user_id=user_id,
                tank_id=tank_id,
                source_event_id=None,
                reminder_type=reminder_type,
                title=title,
                due_at=_at(due_on, hour=9),
                completed_at=None,
                snoozed_until=None,
            )
        )


def _add_event(
    session: Session,
    *,
    user_id: int,
    tank_id: int,
    event_type: str,
    title: str,
    occurred_at: datetime,
    notes: str | None,
) -> EventModel:
    event = EventModel(
        user_id=user_id,
        tank_id=tank_id,
        event_type=event_type,
        title=title,
        occurred_at=occurred_at,
        notes=notes,
        metadata_json={"demo": True},
    )
    session.add(event)
    session.flush()
    return event


def _at(day: date, *, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour, tzinfo=UTC))


def _decimal(value: float) -> Decimal:
    return Decimal(f"{value:.3f}")
