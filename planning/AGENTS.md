# Repository Guidelines

## Project Structure & Module Organization
Root files such as `.env.example`, `Makefile`, `docker-compose.yml`, and the `requirements/` subsets define the shared configuration and dependency surface for API, worker, and dev builds. Production FastAPI code lives under `app/` (with `api/`, `services/`, `db/`, and `workers/` subpackages), Alembic migrations live in `alembic/versions/`, and Kubernetes plus monitoring manifests are staged under `deploy/`. Lightweight helpers and orchestration scripts are kept in `scripts/`, while `tests/` mirrors the API surface (`test_api_health.py`, migration smoke tests) alongside shared fixtures (`tests/conftest.py`).

## Build, Test, and Development Commands
- `make setup` → installs `requirements/dev.txt` and boots `pre-commit` hooks so `ruff`, `mypy`, and other checks run locally.
- `make up` → builds and detaches the dev stack (`api`, `db`, `prometheus`, `grafana` via `docker-compose up -d --build`) and runs `alembic upgrade head` when Postgres is ready.
- `make down` → stops the compose services.
- `make migrate` & `make revision -m "msg"` → apply or create Alembic migrations.
- `make fmt` → enforces formatting (the same `ruff` config used in CI).
- `make lint` → runs `ruff lint` against `app/` and `tests/`.
- `make typecheck` → runs `mypy` with the project’s `python_version = 3.11` baseline.
- `make test` → executes `pytest` over `tests/`.
- `make api` → launches the FastAPI app locally for manual smoke checks (`http://localhost:8000/healthz` and `/metrics`).
- `make seed` → injects the provided sample dataset (used by onboarding and demo flows).

## Coding Style & Naming Conventions
All Python code targets 3.11 and follows four-space indentation, `snake_case` for functions/variables, and `PascalCase` for Pydantic/SQLAlchemy models (e.g., `Paper`, `Repository`). Vector columns and JSONB fields stay explicit in `db/models`, while service helpers under `lib/`/`services/` favor descriptive, testable functions. `ruff`, `mypy`, and the `pre-commit` configuration enforce linting, typing, and security checks before pushes, and the Makefile injects the repository root into `PYTHONPATH` so imports stay consistent.

## Testing Guidelines
`pytest` is the mirror for both unit and integration smoke suites; keep test files named `test_*.py` and reuse `tests/conftest.py` fixtures for shared DB/session setup. Focus coverage on API routes, worker entrypoints, and migration rollbacks; add tests for new scoring or ingestion behaviors before merging. Run `make test` locally before pushing and confirm the same suite passes in CI with lint/typecheck steps.

## Commit & Pull Request Guidelines
Use short, imperative commits (e.g., `Add arxiv ingestion checkpoint logs`), tie each change to the ongoing milestone (M1–M5 from the implementation plan) or issue, and mention any required manual follow-ups in the body. PRs should describe what was built, list the commands used to verify it (`make test`, `make lint`, etc.), and attach any relevant data such as sample logs or metrics dashboards. Expect the CI workflow to gate on lint, typecheck, tests, and migration validation; rerun locally before request.

## Security & Configuration Tips
Store secrets in environment variables (`DATABASE_URL`, `GITHUB_TOKEN`) and keep `.env.example` in sync with required keys; the local stack uses `pgvector` via the `pgvector/pgvector:pg15` Docker image. Avoid checking in credentials, rely on `deploy/k8s/*` secrets, and use `scripts/wait-for-db.sh` when scripts need Postgres readiness. Prometheus/Grafana live under `deploy/monitoring/`—update their configs when adding new metrics.
