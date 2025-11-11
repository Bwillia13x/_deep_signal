DeepTech Radar — Pre‑kickoff documentation and plan

Section 1: Project charter

- Vision: Aggregate frontier research and OSS signals to detect emerging deep‑tech opportunities early.
- Objectives (MVP):
  - Ingest arXiv papers and GitHub repos hourly/daily.
  - Store metadata, vector embeddings, and searchable text in Postgres with pgvector and FTS.
  - Compute domain metrics and weekly “opportunities” with transparent, reproducible scores.
  - Expose FastAPI endpoints for search and exploration with Prometheus metrics and CI/CD.
- Success criteria:
  - T0: Stable ingestion with >95% success per run, deduplication, and idempotency.
  - T1: Vector search latency p95 < 150 ms for k<=20 on 100k+ papers.
  - T2: Weekly opportunity report generated automatically, retriable, auditable.
  - T3: On‑call ready: dashboards + alerts for ingestion failures, DB health, and API SLOs.

Section 2: Scope

- In scope (MVP):
  - Data ingestion from arXiv (categories: cs.AI, cs.LG initially, configurable).
  - GitHub ingestion of repos relevant to those domains via topic/keyword search and paper linking heuristics.
  - Vector embeddings of titles/abstracts with sentence-transformers; cosine similarity search.
  - Domain taxonomy, keyword tagging, and weekly scoring pipeline for “opportunities”.
  - REST API for health, search, similarity, repositories, opportunities; metrics endpoint; CI; Docker; K8s manifests; Grafana/Prometheus.
- Out of scope (MVP):
  - Full UI or public portal.
  - Advanced ML classification beyond keyword and simple model baselines.
  - Cross-lingual and PDF full‑text OCR.
  - Advanced deduplication across multiple bibliographic sources.
- Assumptions:
  - arXiv and GitHub APIs sufficient for MVP; rate limits manageable with ETags, If‑Modified‑Since, and backoff.
  - Cosine similarity on normalized embeddings.
  - Weekly cadence for opportunity scoring.

Section 3: Stakeholders and RACI

- Product/PM: Accountable for prioritization, acceptance, roadmap.
- Tech lead: Accountable for architecture, quality, non‑functional requirements.
- Backend engineers: Responsible for ingestion, API, DB, pipelines.
- DevOps/SRE: Responsible for CI/CD, infra, observability, runbooks.
- Data/ML engineer: Responsible for embeddings, domain classification, scoring models.
- Reviewer(s): Consulted on design reviews and data governance.
- Users/Analysts: Informed; provide feedback and domain insight.

Section 4: Architecture overview

- Components:
  - API service (FastAPI, SQLAlchemy): query/search, health, metrics.
  - Postgres 15 + pgvector: storage for entities and embeddings; FTS with tsvector and pg_trgm.
  - Workers (K8s CronJobs): arxiv_hourly, github_hourly, linking_job, scoring_daily, opportunities_daily.
  - Observability: Prometheus scrape /metrics, Grafana dashboards.
  - CI: GitHub Actions for lint, typecheck, tests, migrations; container builds.
- Data flow (high level):
  - arXiv feed -> fetch with ETag/Last‑Modified -> upsert papers -> embed -> update pgvector/FTS.
  - GitHub API -> fetch repos by keywords/topics and via reference extraction -> upsert repos -> compute repo metrics (stars velocity, CUDA flags, etc.).
  - Linking job -> join papers and repos via textual and reference heuristics -> confidence/evidence.
  - Scoring -> compute domain metrics (weekly windows) and opportunity scores -> persist reports.
- Storage notes:
  - Embeddings stored in pgvector(384); normalized to unit length; cosine distance.
  - Index: HNSW with vector_cosine_ops; FTS GIN on tsvector.

Section 5: Data sources and ingestion plan

- arXiv:
  - Source: OAI-PMH or arXiv API; use categories from env ARXIV_CATEGORIES; pull incremental using updated_after and pagination.
  - Rate limits: polite crawling; sleep on 429; backoff with jitter.
  - Caching: persist ETag/Last‑Modified in http_cache table; skip fetch if 304.
  - Upsert keys: external_id = arXiv ID; DOI optional; conflict targets on external_id.
  - Fields: title, abstract, authors (later), categories -> domain, keywords; published_at.
  - Embeddings: Title + abstract concatenated; normalized; persisted same transaction.
  - Idempotency: use transaction per batch; resume tokens for OAI if used; store checkpoints.
- GitHub:
  - Search heuristics:
    - Repo discovery: search by topics, language filters, and curated keyword patterns; periodic top‑N stars in domain.
    - Reference discovery: search code/issues/README mentions of “arXiv:”, DOI, or paper titles using exact and fuzzy matching.
  - Rate limits: token from GITHUB_TOKEN; respect X-RateLimit-*; conditional requests with ETags.
  - Upsert keys: full_name unique; track stars/forks/issues, topics, language, timestamps.
  - Velocity: compute rolling 30/90‑day star growth slope; store velocity_score and velocity_evidence JSON.
- Linking paper↔repo:
  - Evidence: explicit arXiv/DOI mention; title fuzzy match; author ↔ committer overlap; citation files; dataset/model cards.
  - Confidence: weighted sum; store evidence JSON; recalculable.

Section 6: Domain taxonomy and keyword tagging

- Domain mapping:
  - Start from arXiv categories to coarse domains (e.g., cs.AI -> “AI/ML”; cs.LG -> “ML/Optimization”).
  - Keyword taxonomy seed list (env override): transformer, diffusion, PDE, quantum, photonics, graph, RL, CUDA, FPGA, NeRF, etc.
- Tagging method:
  - Extract keywords from title/abstract via RAKE‑like or noun‑phrase heuristics plus curated list; deduplicate; lowercase; keep top‑K.
  - Domain assignment: majority vote by category and keyword hits; fallback to “unknown”.
  - Provide overrides via config file or DB table in future.

Section 7: Scoring framework and opportunity generation

- Definitions:
  - Novelty: rarity of keywords and semantic distance from last N weeks’ centroid.
  - Momentum: slope of paper count and repo velocity; recency weighted.
  - Repo coverage: number and quality (stars growth, maintenance) of repos linked to topic.
- Formulas (initial baseline, to be refined):
  - novelty_score = zscore(cosine_distance_to_recent_centroid) bounded [0,1].
  - momentum_score = sigmoid(w1*paper_growth + w2*repo_velocity_mu).
  - opportunity_score = wN*novelty + wM*momentum + wR*repo_coverage + wP*paper_count_norm.
  - Store component_scores as JSON with weights and inputs for auditing.
- Cadence:
  - Weekly job computes per-domain metrics and assembles top opportunities with summaries.
  - Summaries: template‑based executive_summary pulling top papers/repos and metric highlights.

Section 8: Data model confirmation and adjustments

- Papers: add unique index on external_id; confirm tsvector trigger configured; OK.
- Repositories: full_name unique; velocity fields nullable; OK.
- Links: composite PK (paper_id, repo_id) with confidence; OK.
- Domain metrics: primary key on (domain, window_start, window_end); OK.
- Opportunities: unique slug + week_of; OK.
- Http cache: url unique; ETag/Last‑Modified present; OK.
- Adjustment to consider before start:
  - pgvector HNSW index should specify cosine ops if using normalized embeddings. Recommended DDL:
    - CREATE INDEX ix_papers_embedding_hnsw ON papers USING hnsw (embedding vector_cosine_ops);
  - Confirm pg_trgm is installed; already ensured in migration.
  - Add indexes on repositories(language), papers(domain, published_at) if needed for filters.
  - Consider partial index on papers where embedding IS NOT NULL.

Section 9: API contracts for MVP

- GET /healthz -> {status}
- GET /readyz -> {status}
- GET /metrics -> Prometheus text
- GET /papers
  - Query: q (text search), limit, offset
  - Response: list of PaperOut {id, external_id, title, abstract, domain, keywords}
- GET /papers/near
  - Query: text_query or paper_id, k
  - Response: list of {id, title, similarity}
- GET /repositories
  - Query: q (later), language, limit, offset
  - Response: list of repos with basic fields
- GET /opportunities
  - Query: week_of (optional), domain (optional)
  - Response: list of {slug, domain, score, component_scores, key_papers, related_repos, week_of}
- Backward compatibility: versioned path /v1 in future when contracts stabilize.

Section 10: Non‑functional requirements

- Performance:
  - p95 API latency < 200 ms for primary endpoints on typical loads.
  - Vector search p95 < 150 ms for k<=20 at 100k+ vectors; index tuned accordingly.
- Availability: 99.9% monthly for API.
- Scalability: Support 1M+ vectors by tuning HNSW and vertical scaling; shard later if needed.
- Reliability: Idempotent ingestion; exactly‑once per item semantics via upsert + checkpoints.
- Cost: Single Postgres instance (2–4 vCPU, 8–16 GB RAM) initially; GPU not required.

Section 11: Observability plan

- Metrics to emit:
  - api_requests_total, api_request_latency_seconds by path/method/status.
  - worker_job_runs_total{job, status}, worker_job_duration_seconds.
  - ingestion_items_processed_total{source}, ingestion_errors_total{source, reason}.
  - embedding_time_seconds, embedding_queue_depth (if batching later).
  - db_pool_in_use, db_pool_overflow (via SQLAlchemy events or exporter).
- Dashboards (Grafana):
  - API overview: requests, latency, error rate, top endpoints.
  - Ingestion: items/hour, success vs error, fetch status codes, retry counts.
  - DB: connections, CPU, query time (add PG exporter in future).
  - Opportunities: weekly scores trend, domain metrics.
- Alerts (Prometheus rules to add):
  - API 5xx rate > 2% for 5m.
  - Job failure count > 0 in 1h or job staleness > 2x schedule.
  - DB unavailable or connection errors spike.
  - Ingestion 304/200 ratio anomalies or sudden drop in items processed.

Section 12: Security and privacy

- Secrets:
  - Use K8s Secrets for DATABASE_URL and GITHUB_TOKEN; avoid committing secrets.
  - Local dev via .env; pre‑commit checks for accidental secrets.
- Access:
  - CORS configured to specific origins in prod; "*" only in dev.
  - Network: restrict DB ingress to API and workers.
- Data:
  - No PII targeted; adhere to arXiv/GitHub TOS; honor robots and polite rates.
- Supply chain:
  - Pin Python deps; enable Dependabot; run Bandit; consider SLSA later.
- AuthZ/AuthN:
  - MVP public unauthenticated API; add API keys or OAuth in Phase 2.

Section 13: Environments and CI/CD

- Environments:
  - Dev: docker-compose with pgvector, Prometheus, Grafana.
  - CI: pgvector service, alembic upgrades, tests, lint, typecheck.
  - Staging/Prod: K8s with API Deployment, CronJobs for workers, Prometheus/Grafana.
- CI:
  - Lint: ruff, black, isort.
  - Typecheck: mypy.
  - Tests: pytest; migration up/down test.
  - Build: container images api and worker; push to registry.
- CD:
  - GitHub Actions workflow to build and push images on main; deploy via ArgoCD or kubectl apply (later).

Section 14: Testing and QA strategy

- Unit tests: services (embeddings fallback), CRUD, scoring functions.
- Integration tests: alembic migrations, vector search queries, FTS filtering.
- Contract tests: basic API response schema checks.
- E2E (staging): run workers on a subset; verify metrics and DB side effects.
- Data correctness:
  - Idempotency tests for upsert.
  - Linker confidence distribution sanity checks and golden samples.
- Performance tests: vector search latency; ingestion throughput with mocks.

Section 15: Runbooks

- Worker failure:
  - Inspect logs; check Prometheus job failure metrics; re‑run job with backfill flag; verify checkpoint state.
- DB migration:
  - Backup; apply alembic upgrade; verify schema; rollback path tested in CI.
- API incident:
  - Check healthz/readyz; scale replicas; verify DB connections; check error spikes; roll back image if needed.
- Token exhaustion:
  - Check rate limit headers; pause job; rotate token; reschedule.

Section 16: Risks and mitigations

- API rate limits or format changes:
  - Mitigation: cache with ETags, exponential backoff, decouple parsers behind adapters.
- Vector index performance degradation:
  - Mitigation: cosine opclass, index tuning (m, ef), periodic reindex; batch embedding to reduce write churn.
- Data drift and noisy linking:
  - Mitigation: conservative confidence thresholds; human‑curated exceptions list; monitor precision via samples.
- Schema evolution:
  - Mitigation: alembic with compare_type; blue/green migrations for breaking changes.
- Model dependency sizes:
  - Mitigation: build separate worker image; lazy load model; keep API image slim.
- Missing dependency in repo:
  - pydantic‑settings must be added to requirements; action below.

Section 17: Backlog (epics and key tasks with initial estimates)

- Epic A: Ingestion foundations (10–12 days)
  - A1: arXiv client with OAI/API, ETag/Last‑Modified, checkpoints, retries (2–3d)
  - A2: Upsert pipeline for papers with embedding compute and transactional writes (2d)
  - A3: GitHub discovery by keywords/topics with pagination, ETags, retries (2–3d)
  - A4: Reference extraction and enrichment (regex, fuzzy match) (2–3d)
  - A5: Backfill tooling for ranges and dry‑run (1d)
- Epic B: Linking and scoring (8–10 days)
  - B1: Paper‑repo linker with evidence and confidence (2–3d)
  - B2: Repo velocity calculator with rolling windows (1–2d)
  - B3: Domain metrics weekly computation (2d)
  - B4: Opportunity scoring and summarization (2–3d)
- Epic C: API and search UX (4–6 days)
  - C1: Repositories and opportunities endpoints with filters and paging (2d)
  - C2: Papers search filters and FTS tuning (1–2d)
  - C3: Rate limiting and pagination consistency (1–2d)
- Epic D: Observability and ops (4–6 days)
  - D1: Prometheus metrics for workers; standard labels; histogram buckets (1–2d)
  - D2: Grafana dashboards and alert rules (1–2d)
  - D3: Runbooks and on‑call docs (1–2d)
- Epic E: Delivery (3–4 days)
  - E1: Dockerized workers and K8s CronJobs with schedules and envs (1–2d)
  - E2: CI container builds and image versioning, provenance (1–2d)
- Epic F: Quality (ongoing)
  - F1: Unit/integration tests to 70%+ coverage, golden datasets (ongoing)

Section 18: MVP acceptance criteria

- Data:
  - At least 50k papers ingested across configured categories with embeddings in DB.
  - At least 5k repos identified; 500+ verified links to papers.
- API:
  - Search and similarity endpoints return results under stated latency; 99% uptime across a week.
- Scoring:
  - Weekly opportunities produced with component breakdown and consistent ranks week‑over‑week on unchanged data.
- Ops:
  - Dashboards live; 3 key alerts configured; runbooks reviewed; CI green; migrations run clean in staging.

Section 19: Open decisions and required inputs

- Confirm target domains for phase 1 beyond cs.AI and cs.LG.
- Confirm embedding model; default is all‑MiniLM‑L6‑v2; consider e5‑base‑v2 or bge‑small if better for scientific text.
- Confirm similarity metric; plan: cosine on normalized vectors; requires cosine opclass index.
- Confirm weekly job schedule (UTC Monday 00:15?) and report audience.
- Confirm API exposure (internal vs public) and auth requirements if public.
- Confirm cost envelope and hosting environment.

Section 20: Immediate repo fixes before kickoff

- Add missing dependency:
  - Add pydantic‑settings==2.x to requirements/base.txt and rebuild.
- Vector index:
  - Update alembic migration to specify vector_cosine_ops or create a new revision altering index to cosine.
- Prometheus exporter:
  - Add worker metrics counters and histograms in workers scaffolding.
- Secrets:
  - Add K8s Secret template and docs for DATABASE_URL and GITHUB_TOKEN; ensure not committed.
- Tests:
  - Add minimal integration test that inserts a vector and queries /papers/near with a deterministic embedding stub.
- CI:
  - Add container build workflow producing ghcr.io images with SHA tags; optionally environment‑specific tags.

Section 21: Timeline (4–6 weeks indicative)

- Week 1:
  - Finalize decisions; repo fixes; implement arXiv ingestion and paper upsert + embeddings; worker metrics.
- Week 2:
  - GitHub discovery and enrichment; link extraction heuristics; initial linker.
- Week 3:
  - Velocity metrics; domain metrics weekly job; opportunity scoring v1; API endpoints for repos/opportunities.
- Week 4:
  - Observability dashboards and alerts; performance tuning; backfill; QA and staging dry‑runs.
- Week 5–6 (buffer/Phase 1.5):
  - Improve linking precision; refine scoring; add auth/caching if needed; production rollout.

Section 22: Communication plan

- Standups: daily during build weeks; async updates otherwise.
- Weekly demo: share ingestion and scoring outputs.
- Incident channel: #deeptech‑ops with on‑call rotation.
- Design reviews: before major schema or scoring changes.

Section 23: Definition of Ready and Done

- DoR:
  - User story defined with acceptance criteria, sample inputs/outputs, and non‑functional expectations; data source confirmed; feature flags noted.
- DoD:
  - Code reviewed; tests added and passing; migrations applied in CI; docs updated; metrics emitted; runbook updated; feature behind config if risky.

Section 24: Kickoff checklist

- Repos and permissions ready; CI secrets configured; container registry access confirmed.
- .env populated locally; K8s Secrets created in staging/prod.
- Grafana and Prometheus reachable; dashboards provisioned.
- Confirm arXiv and GitHub rate limit expectations; tokens valid.
- Agree on domain list, schedule, and acceptance criteria.

If you want, I can:

- Patch the repo with pydantic‑settings, cosine opclass index migration, and a basic worker metrics scaffold.
- Draft initial Grafana panels JSON for ingestion and API.
- Expand the backlog into GitHub Issues with labels, estimates, and dependencies.
