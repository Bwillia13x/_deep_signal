PY=python3
PIP=pip

export PYTHONPATH := $(shell pwd)

.DEFAULT_GOAL := help

help:
	@echo "make setup       - install dev deps"
	@echo "make up          - start dev stack (api, db, prometheus, grafana)"
	@echo "make down        - stop dev stack"
	@echo "make migrate     - alembic upgrade head"
	@echo "make revision    - alembic revision -m 'msg'"
	@echo "make fmt         - format code"
	@echo "make lint        - ruff lint"
	@echo "make typecheck   - mypy"
	@echo "make test        - pytest"
	@echo "make api         - run api locally"
	@echo "make seed        - seed sample data"

setup:
	$(PIP) install -r requirements/dev.txt
	pre-commit install

up:
	docker-compose up -d --build
	@scripts/wait-for-db.sh db 5432
	docker-compose exec api alembic upgrade head

down:
	docker-compose down -v

migrate:
	alembic upgrade head

revision:
	alembic revision -m "$(m)"

fmt:
	black .
	isort .
	ruff check --fix .

lint:
	ruff check .

typecheck:
	mypy .

test:
	pytest -q

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

seed:
	$(PY) scripts/seed_dev_data.py
