from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_production_postgresql_is_internal_and_persistent() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.prod.yml").read_text())
    database = compose["services"]["db"]

    assert database["image"] == "postgres:17-bookworm"
    assert "ports" not in database
    assert "aquaops_postgres:/var/lib/postgresql/data" in database["volumes"]
    assert database["healthcheck"]["test"][0] == "CMD-SHELL"


def test_production_web_uses_configured_postgresql_url_and_migrated_startup() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.prod.yml").read_text())
    web = compose["services"]["web"]

    assert "sqlite" not in web["environment"]["DATABASE_URL"].lower()
    assert web["environment"]["AUTO_CREATE_TABLES"] == "false"
    assert web["depends_on"]["db"]["condition"] == "service_healthy"
    assert "AQUAOPS_IMAGE_TAG:?" in web["image"]
