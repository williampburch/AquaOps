.PHONY: install dev test lint format migrate revision seed-demo backup restore deploy deploy-image deploy-build

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .
	black --check .

format:
	ruff check . --fix
	black .

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(message)"

seed-demo:
	aquaops seed-demo

backup:
	scripts/postgres-backup.sh $(BACKUP)

restore:
	scripts/postgres-restore.sh "$(DUMP)" --confirm-db "$(CONFIRM_DB)"

deploy:
	scripts/deploy-image.sh

deploy-image:
	scripts/deploy-image.sh

deploy-build:
	scripts/deploy-container.sh
