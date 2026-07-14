from __future__ import annotations

import json
from collections.abc import Generator
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.main import create_app
from app.web.dependencies import get_db


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    settings = Settings(
        secret_key="test-secret-key-that-is-long-enough",
        database_url="sqlite+pysqlite:///:memory:",
        auto_create_tables=False,
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders_public_empty_state(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "AquaOps" in response.text
    assert "No events yet" in response.text
    assert "Latest Water Parameters" in response.text
    assert "fertilizer" not in response.text.lower()


def test_register_creates_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "username": "will",
            "email": "will@example.com",
            "password": "a-long-test-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "aquaops_session" in response.cookies


def test_tanks_require_authentication(client: TestClient) -> None:
    response = client.get("/tanks", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_events_and_reports_require_authentication(client: TestClient) -> None:
    events_response = client.get("/events", follow_redirects=False)
    reports_response = client.get("/reports", follow_redirects=False)
    livestock_response = client.get("/livestock", follow_redirects=False)
    plants_response = client.get("/plants", follow_redirects=False)
    notifications_response = client.get("/notifications", follow_redirects=False)
    settings_response = client.get("/settings", follow_redirects=False)
    export_response = client.get("/settings/export", follow_redirects=False)
    quick_log_response = client.get("/quick-log", follow_redirects=False)

    assert events_response.status_code == 303
    assert events_response.headers["location"] == "/login"
    assert reports_response.status_code == 303
    assert reports_response.headers["location"] == "/login"
    assert livestock_response.status_code == 303
    assert livestock_response.headers["location"] == "/login"
    assert plants_response.status_code == 303
    assert plants_response.headers["location"] == "/login"
    assert notifications_response.status_code == 303
    assert notifications_response.headers["location"] == "/login"
    assert settings_response.status_code == 303
    assert export_response.status_code == 303
    assert export_response.headers["location"] == "/login"
    assert quick_log_response.status_code == 303
    assert quick_log_response.headers["location"] == "/login"
    assert settings_response.headers["location"] == "/login"


def test_dashboard_metric_cards_link_to_detail_pages(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/tanks"' in response.text
    assert 'href="/events"' in response.text
    assert 'href="/livestock"' in response.text
    assert 'href="/plants"' in response.text


def test_create_tank_seeds_target_ranges(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/tanks",
        data={
            "name": "Display Tank",
            "tank_type": "planted",
            "volume_liters": "75",
            "started_on": "2026-07-09",
            "description": "Office aquarium",
            "lighting": "LED",
            "filtration": "Canister",
            "substrate": "Aquasoil",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/tanks/1"

    detail = client.get("/tanks/1")
    assert detail.status_code == 200
    assert "Display Tank" in detail.text
    assert "Target Ranges" in detail.text
    assert "Ammonia" in detail.text
    assert "Nitrate" in detail.text


def test_log_water_test_updates_latest_readings_and_charts(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    response = client.post(
        "/tanks/1/water-tests",
        data={
            "occurred_at": "2026-07-09T08:30",
            "ammonia": "0",
            "nitrite": "0",
            "nitrate": "20",
            "ph": "7.4",
            "temperature": "78",
            "kh": "5",
            "gh": "8",
            "tds": "180",
            "notes": "First full test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    detail = client.get("/tanks/1")
    assert "20.000 ppm" in detail.text
    assert "Water Trends" in detail.text
    assert "chartSeries" in detail.text
    assert "First full test" not in detail.text


def test_mobile_quick_log_renders_focused_actions(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    response = client.get("/quick-log?action=water_change&tank_id=1")

    assert response.status_code == 200
    assert "Log it while you are at the tank." in response.text
    assert "Water Change" in response.text
    assert "Water Test" in response.text
    assert "Maintenance" in response.text
    assert "Feeding" in response.text
    assert "Observation" in response.text
    assert "Display Tank" in response.text
    assert 'inputmode="decimal"' in response.text
    assert 'href="/quick-log"' in response.text


def test_quick_log_water_change_saves_percentage_and_optional_details(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)

    response = client.post(
        "/quick-log/water-change",
        data={
            "tank_id": "1",
            "percentage": "25",
            "conditioner_used": "on",
            "substrate_vacuum": "on",
            "notes": "Weekly reset",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        "/quick-log?action=water_change&tank_id=1&saved=water_change"
    )

    confirmation = client.get(response.headers["location"])
    assert "Saved." in confirmation.text
    events = client.get("/events")
    assert "Water Change" in events.text
    assert "Conditioner used, Substrate vacuumed. Weekly reset" in events.text


def test_quick_log_shows_validation_without_losing_water_test_values(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)

    empty_response = client.post(
        "/quick-log/water-test",
        data={"tank_id": "1", "notes": "Kit ready"},
    )

    assert empty_response.status_code == 400
    assert "Nothing was saved." in empty_response.text
    assert "At least one water parameter is required" in empty_response.text
    assert "Kit ready" in empty_response.text

    saved_response = client.post(
        "/quick-log/water-test",
        data={"tank_id": "1", "ammonia": "0", "nitrate": "18"},
        follow_redirects=False,
    )
    assert saved_response.status_code == 303
    detail = client.get("/tanks/1")
    assert "18.000 ppm" in detail.text


def test_quick_log_saves_non_water_maintenance(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    response = client.post(
        "/quick-log/maintenance",
        data={
            "tank_id": "1",
            "maintenance_type": "filter_cleaning",
            "equipment_name": "Canister filter",
            "duration_minutes": "15",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    events = client.get("/events")
    assert "Filter Cleaning" in events.text


def test_quick_log_surfaces_recent_values_without_relogging_old_tests(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)
    client.post(
        "/quick-log/water-change",
        data={"tank_id": "1", "volume_changed": "10"},
    )
    client.post(
        "/quick-log/water-test",
        data={"tank_id": "1", "nitrate": "18"},
    )
    client.post(
        "/quick-log/maintenance",
        data={
            "tank_id": "1",
            "maintenance_type": "filter_cleaning",
            "equipment_name": "Canister filter",
        },
    )

    water_change = client.get("/quick-log?action=water_change&tank_id=1")
    water_test = client.get("/quick-log?action=water_test&tank_id=1")
    maintenance = client.get("/quick-log?action=maintenance&tank_id=1")

    assert 'data-last-volume="10.0"' in water_change.text
    assert "Use 10.0 gal" in water_change.text
    assert "Last 18.000 ppm" in water_test.text
    assert "Canister filter" in maintenance.text
    assert 'data-equipment-name="Canister filter"' in maintenance.text
    assert "aquaops-last-tank" in maintenance.text


def test_quick_log_feeding_uses_recent_values_and_repeats_last(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    saved = client.post(
        "/quick-log/feeding",
        data={
            "tank_id": "1",
            "food_name": "Community flakes",
            "amount": "1",
            "unit": "pinch",
            "target_livestock": "Whole tank",
        },
        follow_redirects=False,
    )

    assert saved.status_code == 303
    feeding = client.get("/quick-log?action=feeding&tank_id=1")
    assert 'data-food-name="Community flakes"' in feeding.text
    assert 'data-feeding-target="Whole tank"' in feeding.text
    assert 'data-feeding-unit="pinch"' in feeding.text
    assert "Repeat now" in feeding.text

    repeated = client.post(
        "/quick-log/feeding/repeat",
        data={"tank_id": "1"},
        follow_redirects=False,
    )

    assert repeated.status_code == 303
    events = client.get("/events")
    assert events.text.count("Fed Community flakes") == 2


def test_quick_log_feeding_accepts_multiple_searchable_foods(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    saved = client.post(
        "/quick-log/feeding",
        data={
            "tank_id": "1",
            "food_names": '["Community flakes", "Frozen brine shrimp"]',
            "amount": "1",
            "unit": "portion",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303

    feeding = client.get("/quick-log?action=feeding&tank_id=1")
    assert 'aria-multiselectable="true"' in feeding.text
    assert 'data-food-name="Community flakes"' in feeding.text
    assert 'data-food-name="Frozen brine shrimp"' in feeding.text
    assert 'id="feeding_food_names"' in feeding.text

    events = client.get("/events")
    assert "Fed Community flakes + Frozen brine shrimp" in events.text

    repeated = client.post(
        "/quick-log/feeding/repeat",
        data={"tank_id": "1"},
        follow_redirects=False,
    )
    assert repeated.status_code == 303
    events = client.get("/events")
    assert events.text.count("Fed Community flakes + Frozen brine shrimp") == 2


def test_quick_log_feeding_validates_food_and_records_skip_reason(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)

    invalid = client.post(
        "/quick-log/feeding",
        data={"tank_id": "1", "food_name": "", "notes": "Food ready"},
    )
    assert invalid.status_code == 400
    assert "Food name is required" in invalid.text
    assert "Food ready" in invalid.text

    skipped = client.post(
        "/quick-log/feeding/skip",
        data={"tank_id": "1", "skip_reason": "Weekly fasting day"},
        follow_redirects=False,
    )
    assert skipped.status_code == 303
    events = client.get("/events")
    assert "Skipped feeding" in events.text
    assert "Weekly fasting day" in events.text


def test_quick_log_observation_uses_presets_and_recent_titles(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    form = client.get("/quick-log?action=observation&tank_id=1")
    assert form.status_code == 200
    assert 'data-observation-title="Behavior change"' in form.text
    assert 'data-observation-title="Plant growth"' in form.text

    saved = client.post(
        "/quick-log/observation",
        data={
            "tank_id": "1",
            "title": "Fish hiding",
            "notes": "Tetras stayed behind the driftwood after lights on.",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303

    refreshed = client.get("/quick-log?action=observation&tank_id=1")
    assert 'data-observation-title="Fish hiding"' in refreshed.text
    events = client.get("/events")
    assert "Fish hiding" in events.text
    assert "Tetras stayed behind the driftwood" in events.text


def test_quick_log_observation_requires_a_title_or_details(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    response = client.post(
        "/quick-log/observation",
        data={"tank_id": "1", "title": "", "notes": ""},
    )

    assert response.status_code == 400
    assert "A note title or body is required" in response.text


def test_quick_log_dose_reuses_product_location_and_last_amount(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    saved = client.post(
        "/quick-log/dose",
        data={
            "tank_id": "1",
            "product_name": "Easy Green",
            "dose_amount": "2.5",
            "dose_unit": "mL",
            "location": "Water column",
            "notes": "After water change",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303

    dose = client.get("/quick-log?action=dose&tank_id=1")
    assert 'data-dose-product="Easy Green"' in dose.text
    assert 'data-dose-location="Water column"' in dose.text
    assert "2.500 mL" in dose.text
    assert "Repeat now" in dose.text

    second_tank = client.post(
        "/tanks",
        data={"name": "Shrimp Tank", "tank_type": "planted", "volume_liters": "20"},
        follow_redirects=False,
    )
    assert second_tank.status_code == 303
    other_tank_dose = client.get("/quick-log?action=dose&tank_id=2")
    assert 'data-dose-product="Easy Green"' in other_tank_dose.text

    repeated = client.post(
        "/quick-log/dose/repeat",
        data={"tank_id": "1"},
        follow_redirects=False,
    )
    assert repeated.status_code == 303
    events = client.get("/events")
    assert events.text.count("Dosed Easy Green") == 2


def test_quick_log_dose_validates_required_amount_and_unit(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    missing_amount = client.post(
        "/quick-log/dose",
        data={"tank_id": "1", "product_name": "Flourish", "dose_unit": "mL"},
    )
    assert missing_amount.status_code == 400
    assert "Dose amount is required" in missing_amount.text

    missing_unit = client.post(
        "/quick-log/dose",
        data={"tank_id": "1", "product_name": "Flourish", "dose_amount": "1"},
    )
    assert missing_unit.status_code == 400
    assert "Dose unit is required" in missing_unit.text


def test_dashboard_logo_is_bounded_at_phone_and_tablet_breakpoints(client: TestClient) -> None:
    dashboard = client.get("/")
    response = client.get("/static/css/app.css")

    assert dashboard.status_code == 200
    assert "/static/css/app.css?v=" in dashboard.text
    assert response.status_code == 200
    assert ".hero-brand-mark" in response.text
    assert "max-width: 100%" in response.text
    assert "overflow: hidden" in response.text
    assert ".mobile-brand" in response.text
    assert "height: 1.75rem" in response.text


def test_quick_log_actions_reflow_before_labels_can_overflow(client: TestClient) -> None:
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert "@media (max-width: 1280px)" in response.text
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in response.text
    assert ".quick-log-action strong" in response.text
    assert "min-width: 0" in response.text


def test_tank_detail_quick_logs_daily_care_events(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    feeding_response = client.post(
        "/tanks/1/feedings",
        data={
            "occurred_at": "2026-07-09T09:00",
            "food_name": "Community flakes",
            "amount": "1",
            "unit": "pinch",
            "target_livestock": "Community",
            "notes": "Everyone ate quickly",
        },
        follow_redirects=False,
    )
    maintenance_response = client.post(
        "/tanks/1/maintenance",
        data={
            "occurred_at": "2026-07-09T10:00",
            "maintenance_type": "water_change",
            "volume_changed": "10",
            "duration_minutes": "20",
            "notes": "Routine weekly change",
        },
        follow_redirects=False,
    )
    note_response = client.post(
        "/tanks/1/notes",
        data={
            "occurred_at": "2026-07-09T11:00",
            "title": "New growth",
            "notes": "Crypts pushing new leaves",
        },
        follow_redirects=False,
    )

    assert feeding_response.status_code == 303
    assert maintenance_response.status_code == 303
    assert note_response.status_code == 303

    events = client.get("/events")
    assert "Fed Community flakes" in events.text
    assert "Water Change" in events.text
    assert "New growth" in events.text
    assert "Crypts pushing new leaves" in events.text


def test_tank_schedules_generate_next_care_reminder(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    detail = client.get("/tanks/1")
    assert "Maintenance Schedules" in detail.text

    config_response = client.post(
        "/tanks/1/maintenance-configs",
        data={
            "water_change_enabled": "on",
            "water_change_interval_days": "7",
            "feeding_interval_days": "1",
            "filter_cleaning_interval_days": "30",
            "fertilizer_interval_days": "7",
        },
        follow_redirects=False,
    )
    maintenance_response = client.post(
        "/tanks/1/maintenance",
        data={
            "occurred_at": "2026-07-09T10:00",
            "maintenance_type": "water_change",
            "volume_changed": "10",
        },
        follow_redirects=False,
    )

    assert config_response.status_code == 303
    assert maintenance_response.status_code == 303

    notifications = client.get("/notifications")
    assert "Water Change due" in notifications.text
    assert "Jul 16, 2026" in notifications.text
    assert "Generated from the water changes schedule" in notifications.text

    detail = client.get("/tanks/1")
    assert "Upcoming" in detail.text
    assert "Last: Jul 9" in detail.text
    assert "Next: Jul 16" in detail.text


def test_high_nitrate_recommends_water_change_without_ammonia_noise(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)

    client.post(
        "/tanks/1/targets",
        data={
            "ammonia_min": "0",
            "ammonia_max": "0",
            "ammonia_unit": "ppm",
            "nitrate_min": "0",
            "nitrate_max": "20",
            "nitrate_unit": "ppm",
        },
    )
    client.post(
        "/tanks/1/water-tests",
        data={
            "occurred_at": "2026-07-09T08:30",
            "ammonia": "0.25",
        },
    )

    ammonia_notifications = client.get("/notifications")
    assert "Water change recommended" not in ammonia_notifications.text

    client.post(
        "/tanks/1/water-tests",
        data={
            "occurred_at": "2026-07-09T09:30",
            "nitrate": "25",
        },
    )

    nitrate_notifications = client.get("/notifications")
    assert "Water change recommended" in nitrate_notifications.text
    assert "nitrate 25" in nitrate_notifications.text
    assert "Nitrate was 25 ppm, above target max 20 ppm." in nitrate_notifications.text


def test_events_page_renders_recent_activity(client: TestClient) -> None:
    _register(client)
    _create_tank(client)
    _log_water_test(client)

    response = client.get("/events")

    assert response.status_code == 200
    assert "Activity Stream" in response.text
    assert "Water test" in response.text
    assert "First full test" in response.text


def test_reports_page_renders_event_charts(client: TestClient) -> None:
    _register(client)
    _create_tank(client)
    _log_water_test(client)

    response = client.get("/reports")

    assert response.status_code == 200
    assert "Operations Intelligence" in response.text
    assert "Event Mix" in response.text
    assert "Nitrate Trend" in response.text
    assert "eventMixPayload" in response.text
    assert "nitratePayload" in response.text


def test_inventory_pages_render_empty_state(client: TestClient) -> None:
    _register(client)

    livestock_response = client.get("/livestock")
    plants_response = client.get("/plants")

    assert livestock_response.status_code == 200
    assert "Livestock Inventory" in livestock_response.text
    assert "No livestock yet" in livestock_response.text
    assert plants_response.status_code == 200
    assert "Plant Inventory" in plants_response.text
    assert "No plants yet" in plants_response.text


def test_tank_detail_adds_custom_livestock_and_plants(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    detail = client.get("/tanks/1")
    assert "Add Livestock" in detail.text
    assert "Add Plant" in detail.text

    livestock_response = client.post(
        "/tanks/1/livestock",
        data={
            "common_name": "Ember Tetra",
            "species": "Hyphessobrycon amandae",
            "quantity": "9",
        },
        follow_redirects=False,
    )
    plant_response = client.post(
        "/tanks/1/plants",
        data={
            "common_name": "Java Fern",
            "species": "Microsorum pteropus",
            "quantity": "2",
        },
        follow_redirects=False,
    )

    assert livestock_response.status_code == 303
    assert plant_response.status_code == 303

    livestock = client.get("/livestock")
    plants = client.get("/plants")
    assert "Ember Tetra" in livestock.text
    assert "Hyphessobrycon amandae" in livestock.text
    assert "9" in livestock.text
    assert "Java Fern" in plants.text
    assert "Microsorum pteropus" in plants.text


def test_mobile_inventory_lifecycle_updates_moves_and_preserves_history(
    client: TestClient,
) -> None:
    _register(client)
    _create_tank(client)
    second_tank = client.post(
        "/tanks",
        data={
            "name": "Grow Out",
            "tank_type": "freshwater",
            "volume_liters": "40",
        },
        follow_redirects=False,
    )
    assert second_tank.status_code == 303

    client.post(
        "/tanks/1/livestock",
        data={"common_name": "Ember Tetra", "quantity": "8"},
    )
    client.post(
        "/tanks/1/plants",
        data={"common_name": "Java Fern", "quantity": "2"},
    )

    livestock_page = client.get("/livestock")
    plants_page = client.get("/plants")
    assert "Manage Livestock" in livestock_page.text
    assert "Manage Plants" in plants_page.text
    assert "Manage entry" in livestock_page.text
    assert 'inputmode="numeric"' in livestock_page.text

    livestock_update = client.post(
        "/livestock/1/update",
        data={
            "tank_id": "2",
            "common_name": "Ember Tetra",
            "species": "Hyphessobrycon amandae",
            "quantity": "6",
            "notes": "Moved for grow out",
        },
        follow_redirects=False,
    )
    plant_archive = client.post(
        "/plants/1/archive",
        data={
            "reason": "melted",
            "ended_on": "2026-07-13",
            "notes": "Failed to establish",
        },
        follow_redirects=False,
    )

    assert livestock_update.status_code == 303
    assert "saved=Livestock+updated" in livestock_update.headers["location"]
    assert plant_archive.status_code == 303
    assert "saved=Plant+history+updated" in plant_archive.headers["location"]

    updated_livestock = client.get("/livestock")
    updated_plants = client.get("/plants")
    events = client.get("/events")
    assert "Grow Out" in updated_livestock.text
    assert 'value="6"' in updated_livestock.text
    assert "No plants to manage" in updated_plants.text
    assert "Updated Ember Tetra" in events.text
    assert "Quantity 8 to 6; Moved from Display Tank to Grow Out" in events.text
    assert "Melted: Java Fern" in events.text
    assert "Failed to establish" in events.text


def test_notifications_and_settings_pages_render(client: TestClient) -> None:
    _register(client)

    notifications_response = client.get("/notifications")
    settings_response = client.get("/settings")

    assert notifications_response.status_code == 200
    assert "Care Queue" in notifications_response.text
    assert "No open notifications" in notifications_response.text
    assert settings_response.status_code == 200
    assert "Automation Control" in settings_response.text
    assert "Water Alerts" in settings_response.text
    assert "Plant Care" in settings_response.text
    assert "Download Your Data" in settings_response.text


def test_settings_export_downloads_portable_user_data(client: TestClient) -> None:
    _register(client)
    _create_tank(client)
    client.post(
        "/quick-log/water-test",
        data={"tank_id": "1", "ammonia": "0", "nitrate": "12"},
    )
    client.post(
        "/quick-log/feeding",
        data={"tank_id": "1", "food_name": "Community flakes"},
    )
    client.post(
        "/quick-log/dose",
        data={
            "tank_id": "1",
            "product_name": "Easy Green",
            "dose_amount": "2",
            "dose_unit": "mL",
        },
    )

    response = client.get("/settings/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "aquaops-export-" in response.headers["content-disposition"]
    with ZipFile(BytesIO(response.content)) as export_zip:
        filenames = set(export_zip.namelist())
        assert {
            "manifest.json",
            "account.csv",
            "tanks.csv",
            "events.csv",
            "water_measurements.csv",
            "feeding_details.csv",
            "fertilizer_details.csv",
            "livestock.csv",
            "plants.csv",
        }.issubset(filenames)
        assert "Display Tank" in export_zip.read("tanks.csv").decode()
        assert "Community flakes" in export_zip.read("feeding_details.csv").decode()
        assert "Easy Green" in export_zip.read("fertilizer_details.csv").decode()
        manifest = json.loads(export_zip.read("manifest.json"))
        assert manifest["format"] == "aquaops-portable-export"
        event_manifest = next(
            item for item in manifest["files"] if item["filename"] == "events.csv"
        )
        assert event_manifest["row_count"] == 3


def test_settings_preferences_affect_new_tank_units(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/settings",
        data={
            "unit_system": "metric",
            "volume_unit": "liter",
            "temperature_unit": "C",
            "date_format": "iso",
            "dashboard_density": "compact",
            "reminder_window_days": "21",
            "enable_livestock": "on",
            "enable_plants": "on",
            "enable_reports": "on",
            "enable_notifications": "on",
            "enable_advanced_water": "on",
            "plant_care_mode": "auto",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    create_response = client.post(
        "/tanks",
        data={
            "name": "Metric Display",
            "tank_type": "planted",
            "volume": "120",
        },
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    detail = client.get("/tanks/1")
    assert "120.0 L" in detail.text
    assert "METRIC" in detail.text
    assert 'value="C"' in detail.text


def test_feature_modules_can_be_hidden_from_dashboard(client: TestClient) -> None:
    _register(client)

    client.post(
        "/settings",
        data={
            "unit_system": "us",
            "volume_unit": "gallon",
            "temperature_unit": "F",
            "date_format": "mdy",
            "dashboard_density": "comfortable",
            "reminder_window_days": "14",
            "plant_care_mode": "off",
        },
    )

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/tanks"' in response.text
    assert 'href="/events"' in response.text
    assert 'href="/reports"' not in response.text
    assert 'href="/livestock"' not in response.text
    assert 'href="/plants"' not in response.text
    assert 'href="/notifications"' not in response.text


def test_target_range_status_flags_high_reading(client: TestClient) -> None:
    _register(client)
    _create_tank(client)

    client.post(
        "/tanks/1/targets",
        data={
            "ammonia_min": "0",
            "ammonia_max": "0",
            "ammonia_unit": "ppm",
            "nitrite_min": "0",
            "nitrite_max": "0",
            "nitrite_unit": "ppm",
            "nitrate_min": "0",
            "nitrate_max": "10",
            "nitrate_unit": "ppm",
            "ph_min": "6.5",
            "ph_max": "8.0",
            "ph_unit": "pH",
            "temperature_min": "74",
            "temperature_max": "80",
            "temperature_unit": "F",
            "kh_min": "3",
            "kh_max": "8",
            "kh_unit": "dKH",
            "gh_min": "4",
            "gh_max": "12",
            "gh_unit": "dGH",
            "tds_min": "50",
            "tds_max": "400",
            "tds_unit": "ppm",
        },
    )
    client.post(
        "/tanks/1/water-tests",
        data={
            "nitrate": "25",
        },
    )

    detail = client.get("/tanks/1")

    assert "status-high" in detail.text
    assert "25.000 ppm" in detail.text


def _register(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={
            "username": "aquarist",
            "email": "aquarist@example.com",
            "password": "a-long-test-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _create_tank(client: TestClient) -> None:
    response = client.post(
        "/tanks",
        data={
            "name": "Display Tank",
            "tank_type": "planted",
            "volume_liters": "75",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def _log_water_test(client: TestClient) -> None:
    response = client.post(
        "/tanks/1/water-tests",
        data={
            "occurred_at": "2026-07-09T08:30",
            "ammonia": "0",
            "nitrite": "0",
            "nitrate": "20",
            "ph": "7.4",
            "temperature": "78",
            "kh": "5",
            "gh": "8",
            "tds": "180",
            "notes": "First full test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
