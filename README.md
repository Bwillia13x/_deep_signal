# DeepTech Radar — Repo

- Quickstart
  - Copy `.env.example` to `.env` and adjust
  - `make setup`
  - `make up`
  - Open <http://localhost:8000/healthz>
  - Prometheus <http://localhost:9090>
  - Grafana <http://localhost:3000> (admin/admin)

- Common commands
  - `make migrate`, `make revision m="msg"`, `make test`, `make fmt`

- API
  - `GET /healthz`, `/readyz`, `/metrics`
  - `GET /papers?q=quantum&limit=20`
  - `GET /papers/near?text_query=graph%20neural%20nets&k=10`

- Notes
  - Local Postgres uses pgvector extension via `pgvector/pgvector:pg15` image
  - Embeddings default to a zero vector when the model is missing (worker container includes the model)

_Next steps to ask for:_
- Fill `workers/arxiv_hourly.py` and `github_hourly.py` with real ingestion + ETag caching.
- Add `scoring_daily.py`, `linking_job.py`, `opportunities_daily.py` logic.
- Provide Grafana dashboard panels wired to Prometheus metrics.
- Create a ZIP/tarball or repo PR with these files.
