.PHONY: install dev test lint format migrate revision

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

