DeepTech Radar: Production Architecture v2.0 (Final)

Purpose

- Provide a single, implementation-ready blueprint for the AI Research Opportunities Discovery Platform (DeepTech Radar).
- Aligns and consolidates the attached refined specifications and review corrections.
- Optimized for developer handoff in an IDE: clear components, data model, APIs, jobs, security, observability, performance targets, and runbooks.

Scope (MVP)

- Data sources: arXiv (papers), GitHub (repositories). Others deferred to Phase 2.
- Core analytics: 6-dimensional scoring (Novelty, Momentum, Moat, Scalability, Attention Gap, Network).
- Storage: PostgreSQL 15+ with pgvector 0.5+.
- API: FastAPI read endpoints (papers, repositories, opportunities), vector search.
- Ops: Prometheus metrics, JSON logs, daily backups, alerting.
- Deployment: Docker Compose (dev), Kubernetes-ready (prod).

SLOs and Non-Functional Requirements

- Availability: API 99.9% monthly.
- Latency: P95 /papers < 300 ms; /papers/near < 500 ms at 50k rows.
- Freshness: ingestion hourly; scoring daily; opportunities daily/weekly freeze; data < 24h stale.
- Scale (MVP): 50k–100k papers, 10k+ repos, 50 RPS read traffic.
- Security: TLS in prod, secrets in vault/KMS, tokens least-privilege, no secrets in logs.
- Backups: daily full logical, 30-day retention; quarterly restore drill; target RTO 4h, RPO 24h.

High-Level Architecture

- Ingestion layer
  - arXiv collector: respectful rate limiting, PDF first-5 pages extraction, embeddings, idempotent upserts.
  - GitHub monitor: keyword search, conditional requests with ETags, dependency scan, velocity score, idempotent upserts.
- Storage layer (PostgreSQL + pgvector)
  - Core entities: papers, repositories, paper_repo_links.
  - Analytics: opportunities, keyword_emergence, researcher_metrics, domain_metrics, pipeline_runs, http_cache.
  - Search: full-text (tsvector) + vector (pgvector, HNSW preferred).
- Analytics engine
  - 6D scoring daily with domain normalization and evidence.
  - Paper–repo linking heuristics with confidence and evidence.
  - Keyword emergence tracking weekly; attention normalization by domain.
- API layer (FastAPI)
  - Read endpoints with filters, pagination, ETags, compression, health/ready/metrics.
  - Vector similarity endpoint for semantic discovery.
- Observability and ops
  - JSON logs, structured metrics (Prometheus), Grafana dashboards, alerts.
  - Backups, restore runbook, security controls, CI/CD.

Technology Stack

- Language/runtime: Python 3.11+, asyncio-capable.
- API: FastAPI + Uvicorn/Gunicorn.
- ORM/migrations: SQLAlchemy 2.x + Alembic.
- Database: PostgreSQL 15+; pgvector 0.5+.
- NLP/embeddings: sentence-transformers all-MiniLM-L6-v2 (384-D, cosine).
- HTTP: httpx (ETags, timeouts, backoff with jitter).
- PDF: pypdf (text only, page cap).
- Metrics: Prometheus client; Grafana dashboards.
- Containerization: Docker (Compose for dev), Kubernetes (prod-ready manifests).

Repository Structure (recommended)

- api/ (FastAPI app, routes, schemas)
- workers/ (arxiv_hourly.py, github_hourly.py, scoring_daily.py, linking_job.py, opportunities_daily.py)
- db/ (models, alembic migrations, session)
- lib/ (http client with ETags, embeddings utils, logging, metrics, config)
- infra/ (k8s manifests, backup job, ingress)
- analytics/ (keyword extraction, attention calc, network calc, scorer)
- scripts/ (backfill, seed, smoke tests)
- tests/ (unit, integration, fixtures)
- config/ (weights, lexicons)

Data Model (PostgreSQL)

- Conventions
  - All timestamps timestamptz (UTC).
  - IDs BIGSERIAL unless stated; GitHub IDs BIGINT.
  - All scores constrained to [0,1].
  - Evidence stored as JSONB for audit.
  - Enable pgvector extension.
- papers
  - identity: id, external_id (unique, e.g., arxiv:2411.xxxx), doi (partial unique where not null), source.
  - metadata: title, abstract, text_excerpt (first 3–5 pages), authors (JSONB array), language.
  - publication: published_date, updated_date, arxiv_category.
  - urls: pdf_url, source_url.
  - features: has_code, has_patent, has_pdf, pdf_text_pages, primary_domain (normalized), keywords (JSONB array).
  - embeddings: embedding (vector 384), embedding_model, embedding_dim.
  - scores: moat_score, scalability_score, novelty_score (nullable until computed).
  - evidence: moat_evidence, scalability_evidence (JSONB).
  - search: tsv (tsvector), auto-generated via trigger.
  - lineage: source_meta (JSONB).
  - timestamps: created_at, updated_at, deleted_at.
  - indexes: BRIN on published_date; GIN on tsv, keywords, authors; partial unique doi; composite indexes for common filters; vector index (HNSW preferred; IVFFLAT fallback).
- repositories
  - identity: id, full_name (unique owner/name), github_id (BIGINT unique).
  - metadata: description, topics (text[]), language, license, urls (html_url, clone_url, homepage).
  - metrics: stars, forks, watchers, open_issues.
  - activity: created_at, updated_at, pushed_at.
  - tech: dependencies (JSONB), has_dockerfile, has_ci_cd.
  - scores: deeptech_complexity_score, velocity_score (+ velocity_evidence JSONB optional).
  - timestamps: ingested_at, last_analyzed, deleted_at.
  - indexes: GIN on topics, dependencies; BRIN on pushed_at; stars (partial); updated_at.
- paper_repo_links
  - paper_id (FK), repo_id (FK), confidence [0,1], method (e.g., arxiv_id_match, doi_match, title_fuzzy), evidence JSONB, created_at.
  - constraints: unique (paper_id, repo_id).
  - indexes: by paper_id, repo_id.
- opportunities
  - identity: id, name, slug (unique).
  - classification: primary_domain, technology_cluster (optional).
  - scores (0–1): novelty, momentum, attention_gap, moat, scalability, network; composite_score (indexed).
  - recommendation: STRONG_BUY, BUY, WATCH, PASS.
  - evidence: key_papers (int[]), key_researchers (int[], optional), related_repos (int[]), strengths/risks/comparables (JSONB), investment_thesis, executive_summary, scoring_metadata JSONB.
  - tracking: detected_at, last_updated, status (active, reviewed, passed, invested), created_by; validation outcome fields.
  - indexes: composite (filtered > threshold), (primary_domain, composite), detected_at.
- keyword_emergence
  - identity: id, keyword, normalized_keyword (unique per week_start).
  - window: week_start, week_end.
  - metrics: mention_count, paper_count, domains (text[]), growth_rate, emergence_score.
  - indexes: week, filtered index on emergence_score.
- researcher_metrics
  - identity: id, normalized_name, domain.
  - metrics: degree, centrality (domain-normalized), last_updated.
  - unique: (normalized_name, domain).
- domain_metrics
  - identity: id, domain, metric (novelty|velocity|network|moat|scalability|composite).
  - stats: mean, stddev, sample_size, computed_at; unique (domain, metric, computed_at).
- pipeline_runs
  - identity: id, pipeline_id (unique), pipeline_type (full|incremental).
  - execution: started_at, completed_at, status (running|success|failed|partial).
  - metrics: records_processed JSONB, opportunities_found, errors JSONB, duration_seconds.
  - config snapshot, error_message, stack_trace.
- http_cache
  - primary key: url; etag, last_modified, last_seen

Migrations (Alembic)

- On upgrade:
  - CREATE EXTENSION IF NOT EXISTS vector;
  - Create tables above with constraints and indexes.
  - Create tsvector trigger for papers (weights: title A, abstract B, text_excerpt C).
  - Create HNSW index on papers.embedding (m=16, ef_construction=64); fallback to IVFFLAT (lists=100) via DO block.
  - Partial unique index on doi (WHERE doi IS NOT NULL).
  - ANALYZE after initial load.
- On downgrade: drop triggers, indexes, tables, then DROP EXTENSION vector.

Ingestion Pipelines

- arXiv (workers/arxiv_hourly.py)
  - Rate limit: 1 request per 3 seconds (0.33 req/s). Use arxiv.Client(delay_seconds=3, num_retries=5) plus jitter between categories/pages.
  - Fetch by category list; stop when published < lookback threshold.
  - PDF extraction: pypdf first 3–5 pages; cap 10k chars; if failure, fallback to abstract. Set has_pdf and pdf_text_pages.
  - Domain classification: rule-based keyword matching (configurable), “other” fallback.
  - Keywords: simple noun-phrase heuristics initially; upgradeable to spaCy/KeyBERT.
  - Embeddings: all-MiniLM-L6-v2 (384-D) cosine; normalize; validate EMBEDDING_DIM at startup; persist model name and dim.
  - Upsert: by external_id; update when new fields improve quality (e.g., text_excerpt added); per-item try/except; commit in small batches; metrics recorded.
- GitHub (workers/github_hourly.py)
  - Rate limit: 30 search requests/minute authenticated (2s between calls).
  - Headers: Authorization Bearer; Accept application/vnd.github+json; X-GitHub-Api-Version=2022-11-28; use topics preview Accept if needed.
  - Conditional requests: store ETag in http_cache; send If-None-Match; skip processing on 304.
  - Search: per keyword “in:name,description pushed:>YYYY-MM-DD” with pagination cap; stop rules to respect budget.
  - Enrichment: dependency manifests (requirements.txt, package.json, Cargo.toml) best-effort; deeptech_complexity_score via pattern lexicons; flags for Dockerfile/CI.
  - Velocity score: combine recency (days since pushed), stars (log scale), open_issues; handle null dates with conservative defaults; stale >180d penalty; <7d boost; store evidence.
  - Upsert: by full_name; set detected_at and last_scanned_at; batch commits.

Paper–Repo Linking (workers/linking_job.py)

- Heuristics in descending confidence:
  - README contains arXiv ID (confidence ~0.9).
  - README contains DOI (confidence ~0.95).
  - Title/description fuzzy match, keyword overlap (lower confidence).
- Implementation:
  - Normalize text (lowercase, ASCII fold, tokenize); retrieve README/README.md via GitHub API respecting ETags.
  - Ensure repo exists and has id (insert + flush) before creating links.
  - Store evidence JSON (matched_in, tokens, similarity).
  - Deduplicate via unique (paper_id, repo_id).

Analytics and Scoring (workers/scoring_daily.py)

- Run daily (e.g., 02:00 UTC). Recompute for last N days and optionally backfill.
- Novelty (0–1):
  - Compute cosine distance from paper embedding to domain centroid over trailing window; map to domain-relative percentile; clip extremes to reduce outliers.
- Momentum (0–1):
  - Weighted sum: recency decay (dominant), linked repo attention (normalized stars), co-authorship recency proxy (optional simple heuristic); map and clip.
- Moat (0–1):
  - Pattern-based barriers: equipment, process, material, compute; evidence lists; code/dataset availability penalize replication difficulty; normalize across domain via z-score to [0,1].
- Scalability (0–1):
  - Positive signals: manufacturing-friendly (CMOS-compatible, wafer-scale, room temp, roll-to-roll), economics (yield, cost), maturity (TRL, pilot lines, licensing), IP/code bonus.
  - Blockers: cleanroom-only, manual processes, scarce/toxic materials, regulatory hurdles; net score clipped to [0,1], then domain-normalized.
- Attention Gap (0–1):
  - Technical quality proxy: average of moat and scalability.
  - Attention: domain-relative quantile of attention features (e.g., repo stars and link count).
  - Score: 1 - normalized_attention, centered using technical quality gap where applicable.
- Network (0–1):
  - Compute co-authorship degree/centrality over trailing window using Postgres or NetworkX; average author centrality for paper; add small cross-domain collaboration bonus; normalize by domain.
- Domain normalization:
  - Maintain domain_metrics windows (e.g., trailing 90 days) per metric: mean, stddev, sample_size.
  - z-score clipping at [-2, 2], map via normal CDF to [0,1].
- Composite score (0–1):
  - Default weights sum to 1.0: novelty 0.25, momentum 0.15, attention_gap 0.20, moat 0.20, scalability 0.15, network 0.05.
  - Synergy bonus: +0.02 per metric > 0.7, capped at +0.08.
  - Store per-metric values and weights in scoring_metadata; update papers and feed into opportunities.
- Evidence:
  - Persist explanatory evidence JSON for moat/scalability/linking/attention.

Keyword Emergence and Attention (analytics jobs)

- Keyword emergence (weekly buckets):
  - Weekly aggregate of normalized keywords by domain; compute growth_rate and emergence_score; unique per (keyword, week_start).
- Attention normalization:
  - Domain-relative quantile rank of attention proxies (e.g., repo stars + link weights) to compute normalized_attention; feeds attention_gap.

Opportunities Generation (workers/opportunities_daily.py)

- Compute weekly top-K per domain (e.g., K=20) using composite score thresholds (e.g., >0.65).
- Weekly freeze Monday 00:00 UTC; update current week daily until freeze.
- Deduplicate across weeks to avoid repeats within last 4 weeks (NOT EXISTS window).
- Populate name, slug, primary_domain, component scores, composite_score, recommendation, key_papers, related_repos, strengths/risks, investment_thesis (template or manual initially), executive_summary; set created_by version tag.

API (FastAPI)

- Common
  - Pagination: per_page default 25, max 100; limit and offset or cursor-based if needed.
  - ETags: strong ETag computed from query params + max(updated_at) and/or row count; respond 304 when If-None-Match matches.
  - Compression: gzip for responses >1KB.
  - Validation: Pydantic schema; sanitize inputs; cap limits.
  - Health: /healthz (process), /readyz (DB reachable; domain_metrics freshness).
  - Metrics: /metrics (Prometheus).
- Endpoints
  - GET /papers
    - Params: q (full-text), domain, since (date), min_moat, min_scalability, sort (published|moat|scalability|novelty|composite when available), page/per_page.
    - Returns: list of papers with key fields, evidence flags, authors summary; supports ETag.
  - GET /papers/near
    - Params: text or paper_id; k (default 10).
    - Behavior: embed text or fetch embedding by paper_id; pgvector cosine search; return top-k with similarity scores.
  - GET /repositories
    - Params: q (tsv on name/desc), topics (array), since, min_stars, sort, page/per_page; ETag support.
  - GET /opportunities
    - Params: domain, min_score (default 0.65), recommendation, week_start (optional), page/per_page.
    - Returns: weekly set with component scores and summary.
  - Optional pipeline endpoints (MVP optional, admin-only in prod)
    - POST /pipeline/execute (lookback_days, focus_domains) → start orchestrator job; returns pipeline_id.
    - GET /pipeline/status/{pipeline_id}.
- Security (prod)
  - TLS termination at ingress; optional API key or auth in Phase 2.
  - Rate limiting at ingress (e.g., 100 req/min per IP).
  - CORS configured for dashboard domain(s).

HTTP Client and Rate Limiting (lib/http.py)

- httpx client with:
  - Timeouts, retries with exponential backoff and full jitter (cap max delay).
  - Conditional requests using http_cache: ETag (If-None-Match) and Last-Modified if present.
  - Respect X-RateLimit-Reset; sleep and retry for 403 from GitHub.
  - Request ID propagation in logs.

Observability

- Logging
  - Structured JSON to stdout; include request_id, component, severity, message; exclude secrets.
- Metrics (Prometheus)
  - ingest_arxiv_requests_total, ingest_github_requests_total.
  - rate_limit_sleeps_total{service}, rate_limit_sleep_seconds{service}.
  - db_upserts_total{table}, db_upsert_errors_total{table}.
  - api_requests_total{method,endpoint,status}, api_request_duration_seconds{method,endpoint}.
  - vector_queries_total, vector_query_duration_seconds.
- Dashboards
  - Ingestion: request counts, errors, rate-limit sleeps; papers/repos per hour/day.
  - API latency and throughput; error rates.
  - Vector search latency; index usage if exposed via exporter.
  - Scoring job durations; domain_metrics freshness.
- Alerts
  - No new papers in 24h.
  - GitHub 403 > 20% in 1h.
  - API 5xx > 1% for 5m.
  - Vector P95 > 1s for 15m.
  - Scoring pipeline failed today.
  - Backup failure within last 24h.

Security

- Secrets
  - Store in vault/KMS or Kubernetes Secrets; never hardcode; rotate periodically.
- Network
  - DB not publicly accessible; network policies restricting DB to app namespace.
  - Enforce TLS; DATABASE_URL uses sslmode=require in prod.
- Tokens
  - GitHub token with least-privilege scopes (public_repo sufficient).
- Data handling
  - Input validation; sanitize logs; redact evidence if it could include secrets.
- Dependencies
  - Weekly vulnerability scans; pin versions; supply chain checks.

Backups and Disaster Recovery

- Backups
  - Nightly logical backups (e.g., pg_dump) to object storage with encryption at rest; 30-day retention; versioning enabled.
- Restore drill
  - Quarterly restore to staging; verify integrity; document timings (target RTO 4h, RPO 24h).
- Runbook
  - Document backup paths, restore procedure, verification steps.

Performance and Scale

- Database
  - VACUUM ANALYZE after bulk loads.
  - Use BRIN on time-series columns; GIN on JSONB/array/tsv; tuned pgvector index.
  - pgvector search tuning: set ef_search (e.g., 64–128) for HNSW; tune lists for IVFFLAT.
- API
  - Cap per_page; efficient SELECT lists; leverage ETag and gzip.
- Load tests
  - Seed with 50k papers; test /papers, /papers/near at target RPS; confirm SLOs.
- Application
  - Connection pooling with pool_pre_ping; worker counts tuned based on CPU and I/O.

Configuration (env vars)

- DATABASE_URL
- EMBEDDING_MODEL (default sentence-transformers/all-MiniLM-L6-v2)
- EMBEDDING_DIM (default 384; startup validation against model)
- GITHUB_TOKEN
- ARXIV_DELAY_SECONDS (default 3.0)
- HTTP_TIMEOUT_SECONDS (default 30)
- INGEST_ARXIV_ENABLED, INGEST_GITHUB_ENABLED (true/false)
- MAX_PDF_PAGES (default 5)
- API_PAGE_SIZE_DEFAULT, API_PAGE_SIZE_MAX
- LOG_LEVEL
- PROMETHEUS_PORT (if separate metrics server)

Job Schedules (Kubernetes CronJobs)

- arxiv-hourly: every hour at :05; feature flag controllable.
- github-hourly: every hour at :15; consider different offsets to avoid bursts.
- scoring-daily: daily at 02:00 UTC; writes papers scores + domain_metrics.
- opportunities-daily: daily at 03:00 UTC; updates current week; weekly freeze on Monday 00:00 UTC.
- backup-daily: daily at 02:00 UTC (or infra side).

Testing and Quality Gates

- Unit tests
  - HTTP client ETag behavior and backoff; extractors (moat/scalability) patterns; scoring math; embedding dimension validator.
- Integration tests
  - Alembic migrations (upgrade/downgrade); TSV trigger; vector similarity; API ETag 304 flow; ingestion idempotency.
- Acceptance tests
  - End-to-end: arXiv+GitHub ingested, scores computed, opportunities generated, API returns expected results with latency and pagination.
- Data validation
  - Daily constraint checks: no NULLs where prohibited, score ranges [0,1], domain_metrics freshness, composite weights sum audit.

Rollout Plan

- Staging
  - Deploy full stack; run migrations; seed 7–30 days backfill with rate-limit-aware batches.
  - Enable CronJobs; verify metrics, alerts; load test and tune.
- Production (soft launch)
  - Deploy API and workers; smoke tests; enable ingestion; monitor for 24–48h.
  - Enable daily scoring; verify opportunities; spot-check top items.
- Phase 2 (post-MVP)
  - Semantic Scholar for citation velocity; patents/grants; real-time alerts; auth; caching; read replicas.

Risks and Mitigations

- External API limits: ETags, backoff, token rotation; strict budgets; alert on 403s.
- PDF parsing failures: try/catch per record; abstract fallback; mark has_pdf, pages extracted.
- Embedding/model drift: assert dimension at startup; version embedding_model; migration path for model changes.
- Query performance: indexes, VACUUM ANALYZE, cap per_page, pgvector tuning, monitor P95s.
- Data drift: daily validation; z-score clipping; manual review loop.

Pre-Launch Checklist

- Database: pgvector installed; migrations applied; indexes created; ANALYZE executed; EXPLAIN plans sane.
- Config: env vars set; tokens valid; TLS enforced in prod.
- Ingestion: arXiv and GitHub tested with small lookback; ETags persisted; rate-limit sleeps observed; embeddings valid dimension.
- Scoring: domain_metrics populated; scores in [0,1]; composite distribution bell-shaped around ~0.5; evidence persisted.
- API: /healthz, /readyz, /metrics live; /papers and /papers/near tested with filters and ETag; gzip enabled.
- Observability: Prometheus scraping; dashboards deployed; alerts tested in staging.
- Backups: backup job running; restore drill completed to staging; runbook documented.
- Security: secrets in vault; no tokens in logs; ingress rate limiting in place.
- Performance: load tests pass targets; vector search tuned.

Suggested Development Order (critical path)

1) Migrations and DB smoke tests
2) Shared libs: HTTP client with ETags/backoff, DB session, logging, metrics
3) arXiv ingestion with embeddings and PDF guard
4) GitHub monitor with ETags and velocity
5) Read API (/papers, /repositories, /papers/near) with ETag and gzip
6) Scoring daily job (6D + normalization + composite)
7) Linking job and attention calculations
8) Opportunities generator and endpoint
9) Observability and alerts
10) Backups, security, and performance tuning
11) Production cutover and runbook

Notes and Implementation Hints

- Ensure If-None-Match is set from http_cache per URL; store ETag and Last-Modified; update last_seen on 304.
- Canonicalize query params for API ETags; include max(updated_at) and count hash in the ETag.
- Use BRIN for time-sorted tables (published_date, pushed_at) to accelerate range scans at scale.
- For vector search, pre-normalize embeddings and use cosine ops; prefer HNSW; set ef_search higher for P95 improvements.
- Name normalization for researcher_metrics: Unicode fold, lowercase, remove punctuation, normalize “Last, First” to “First Last”.
- Weekly dedupe in opportunity generation: exclude papers already selected in prior 4 weeks.

Deliverables on Request

- Alembic migration files (001_initial_schema.py) with HNSW→IVFFLAT fallback and tsv trigger.
- FastAPI router stubs and Pydantic schemas for all endpoints.
- Kubernetes manifests (API Deployment/Service/Ingress, CronJobs, backup job).
- GitHub Actions workflows for CI/CD (migrations, tests, build, deploy).
- Grafana dashboards JSON and Prometheus alert rules.
- README with quick start (Docker Compose), runbook, and operations checklists.

If you want me to generate code patches or manifests, say “generate the patches” and share your repo layout and any preferences.
