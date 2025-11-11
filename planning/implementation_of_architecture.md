DeepTech Radar MVP — Phased Implementation Plan

Overview

- Goal: Deliver the MVP described in the Production Architecture v2.0: hourly ingestion (arXiv, GitHub), daily scoring, weekly opportunities, FastAPI read API with vector search, observability, backups, and production-ready deployment.
- Duration: 10 weeks (can compress to 8 with full-time team and no surprises).
- Team roles
  - Tech Lead/Architect (TL)
  - Backend Engineer (BE)
  - Data/ML Engineer (MLE)
  - DevOps/SRE (SRE)
  - QA/Automation (QA)
  - PM/TPM (PM)
- Cadence
  - Weekly milestones and demos.
  - Daily standup; Kanban with WIP limits.
  - “Definition of Done” gates per phase.
  - Staging environment active by end of Week 2.

Milestones (high level)

- M1 (Week 2): DB schema + infra + dev stack stable; migrations green; CI/CD pipeline running; staging live.
- M2 (Week 4): arXiv + GitHub ingestion E2E, embeddings, vector index, API /healthz and /papers basic.
- M3 (Week 6): API v1 (papers, repos, near), scoring daily, linking job.
- M4 (Week 8): Opportunities daily/weekly; dashboards + alerts; backups; staging SLOs pass.
- M5 (Week 10): Load/perf tuned; security hardened; production launch.

Phase 0: Project kick-off and foundations (Week 1)
Objectives

- Repository bootstrapped; dev containers; CI pipeline; base observability and config patterns.
Tasks
- PM: Set up backlog (epics, stories), milestones, acceptance criteria, and comms plan.
- TL: Confirm scope, SLOs, data volume assumptions; finalize domain list and lexicons baseline.
- BE/SRE: Repo scaffold and structure per blueprint; pre-commit hooks; codeowners; branch protections.
- SRE: Docker Compose for dev (API, Postgres 15 + pgvector, Prometheus, Grafana); Makefile targets; dev.env template; secrets strategy documented.
- BE: FastAPI skeleton with /healthz, /readyz, /metrics; structured JSON logging; Pydantic base schemas; error handling middleware.
- QA: Test plan skeleton; acceptance test framework placeholder (pytest + httpx).
Deliverables
- Repo created with structure and coding standards.
- CI: Lint, type check, unit tests, build images.
- Dev environment runs locally end-to-end (API + DB + metrics).
Exit criteria
- One-click dev up: make up completes; /healthz OK; Grafana reachable.
- CI green on main; 80%+ code style coverage.

Phase 1: Database schema, migrations, and seeding (Week 1–2)
Objectives

- Implement full MVP schema with triggers and vector index; validate upgrade/downgrade; seed utilities.
Tasks
- BE: Alembic migration for all tables and indexes as defined; pgvector CREATE EXTENSION; HNSW→IVFFLAT fallback block; partial unique index on doi; tsvector trigger for papers.
- SRE: Dockerfile for DB init; Postgres config tuned for dev; managed service documentation for prod.
- BE: DB access layer (SQLAlchemy 2.x) and session management; connection pooling; pool_pre_ping.
- QA: Integration tests for migrations upgrade/downgrade and basic CRUD.
- BE: Data seeding script for local: small set of papers/repos; ANALYZE after seed; EXPLAIN plans sanity check.
Deliverables
- Alembic 001_initial_schema migration; db smoke test script; seed script; EXPLAIN artifacts.
Exit criteria
- Alembic upgrade/downgrade succeeds; tsvector trigger populates; vector index created with HNSW or IVFFLAT fallback.
- Queries for list endpoints have expected indexes in use.

Phase 2: Shared libraries and observability scaffolding (Week 2)
Objectives

- Common HTTP client with ETags/backoff; logging and metrics libraries; config loaders.
Tasks
- BE: lib/http.py with httpx client; ETag and Last-Modified conditional requests; exponential backoff with jitter; request_id propagation; timeouts.
- BE: Config loader (env vars) with validation (embedding dimension check); feature flags for workers.
- BE: Metrics module with Prometheus counters and histograms named in the blueprint; request middleware for API.
- QA: Unit tests for HTTP client caching logic and backoff paths.
Deliverables
- Shared libs consumed by workers and API; metrics exposed; structured logs consistent across components.
Exit criteria
- Simulated GitHub/arXiv calls exercise ETag paths; metrics visible in Prometheus; no secrets in logs.

Phase 3: arXiv ingestion pipeline (Week 3)
Objectives

- Hourly arXiv ingestion with PDF excerpt, embeddings, domain classification, keywords, idempotent upserts.
Tasks
- MLE: Embedding pipeline using sentence-transformers all-MiniLM-L6-v2; normalization; dimension assertion; singleton model service in worker.
- BE: workers/arxiv_hourly.py with respectful rate limiting; per-category paging; lookback cutoff; per-item try/except.
- MLE: Keyword extraction (simple noun-phrases) and domain classification rules; configurable lexicons.
- BE: PDF extraction via pypdf first 3–5 pages with char cap; abstract fallback; flags for has_pdf, pdf_text_pages.
- BE: Upsert logic by external_id; update when content improves; batch commits; metrics on records processed/errors.
- SRE: CronJob manifest (disabled in prod until staging tested); K8s service account; resource requests.
- QA: E2E test on staging with 1–2 categories and 1 day lookback; check idempotency and metrics.
Deliverables
- ArXiv worker image; staging CronJob; paper records with embeddings in DB.
Exit criteria
- Hourly job runs in staging with <0.5% error rate; records upserted; embeddings populated; tsvector filled; indexes used on queries.

Phase 4: GitHub ingestion pipeline (Week 4)
Objectives

- Hourly GitHub search with ETags and rate-limit handling; enrichment; velocity scoring; repo upserts.
Tasks
- BE: workers/github_hourly.py with authenticated requests; search by keywords/time; pagination cap; conditional requests with http_cache table.
- BE: Enrichment: topics, dependency manifests fetch best-effort; detect Dockerfile and CI; compute deeptech_complexity_score (lexicon-driven); velocity_score with evidence.
- BE: Repo upsert by full_name; set ingested_at, last_analyzed; metrics for requests and upserts.
- SRE: GitHub token secret management; rate-limit budget dashboards; alert on 403 bursts.
- QA: Integration tests with recorded fixtures; ETag 304 path; null fields handling.
Deliverables
- GitHub worker image; staging CronJob; repos enriched and stored; velocity_evidence captured.
Exit criteria
- Hourly job runs in staging with ETag hits on re-runs; dependency parsing doesn’t crash job; repos visible via SQL with metrics populated.

Phase 5: API v1 and vector search (Week 5)
Objectives

- Read endpoints for papers/repositories with filters, ETag support, gzip; vector similarity endpoint.
Tasks
- BE: /papers and /repositories endpoints with pagination, filters, sorting; efficient SELECT lists; ETag computation (query hash + max(updated_at) + row count).
- BE: /papers/near for text or paper_id; pgvector cosine search; top-k with similarity in response.
- BE: Input validation and caps (per_page max); response compression for >1KB.
- SRE: Ingress for staging; CORS for dashboard domain(s); TLS in staging if available.
- QA: API contract tests; ETag 304 tests; latency checks; tsv search relevance sanity.
Deliverables
- FastAPI app with all core endpoints; OpenAPI spec published; simple Postman/insomnia collection.
Exit criteria
- P95 latency in staging: list < 300 ms; near < 500 ms at 5–10k rows; ETag returns 304 when unchanged.

Phase 6: Scoring and domain normalization (Week 6)
Objectives

- Implement 6D scoring with evidence and domain normalization; daily scoring job; domain_metrics table maintenance.
Tasks
- MLE: Implement novelty, momentum, moat, scalability, attention_gap, network calculations per blueprint; z-score clipping; map via CDF to [0,1].
- MLE/BE: scoring_daily.py recomputing last N days; backfill mode; store per-metric values, evidence, embedding reuse.
- BE: domain_metrics maintenance for trailing windows; transactions per domain; auditing.
- QA: Unit tests for metric math; distribution checks; guard for [0,1]; regression tests with synthetic data.
Deliverables
- Scored papers with per-metric values and scoring_metadata; domain_metrics populated; daily CronJob.
Exit criteria
- Score distributions look sane (composite ~bell around 0.5); no NULLs where not allowed; daily job completes <30 minutes on staging dataset.

Phase 7: Paper–repo linking and attention normalization (Week 7)
Objectives

- Link papers and repos with confidence and evidence; compute normalized attention for attention_gap.
Tasks
- BE: linking_job.py implementing heuristics (arXiv ID, DOI, fuzzy title/keyword overlap); README fetch with ETag; normalize text; unique constraints.
- BE: Persist paper_repo_links with evidence and confidence; recompute links incrementally.
- MLE: Attention normalization per domain using link counts and repo attention (stars etc.); feed into scoring_daily.
- QA: Fixtures covering link scenarios; dedup and conflict tests; attention normalization tests.
Deliverables
- Linking job operational; attention normalization integrated; metrics and dashboards for link rates and confidence.
Exit criteria
- Precision in sampled linking >80% at conf ≥0.8; attention_gap responds to changes in repo signals.

Phase 8: Opportunities generation and endpoint (Week 8)
Objectives

- Generate and store weekly top-K opportunities; expose via API; simple narrative fields.
Tasks
- BE: opportunities_daily.py applying thresholds, weekly freeze rules, dedupe across weeks; populate evidence fields (key_papers, related_repos).
- MLE: Executive summary and investment_thesis templating from evidence; configurable thresholds.
- BE: /opportunities endpoint with filters and pagination.
- QA: End-to-end test: new high-scoring paper creates or updates opportunity; weekly freeze respected.
Deliverables
- Opportunities in DB; API returns component scores and summaries.
Exit criteria
- At least one week’s set generated in staging; dedupe logic verified; endpoint P95 < 300 ms.

Phase 9: Observability, backups, and security hardening (Week 9)
Objectives

- Dashboards and alerts; backup automation and restore drill; security controls and docs.
Tasks
- SRE: Grafana dashboards for ingestion, API, scoring, vector search; Prometheus alert rules from blueprint.
- SRE: Nightly pg_dump to object storage; encryption at rest; retention 30 days; restore script and drill to staging.
- SRE: TLS at ingress; DB sslmode=require; Kubernetes manifests for all workers and API; secrets via K8s secrets or vault.
- BE: Redact-sensitive logging; input validation hardening; rate limiting at ingress if available.
- QA: Fire alerts in staging; backup/restore verification; security scan baseline.
Deliverables
- Dashboards, alerts, backup job, restore runbook, Kubernetes manifests.
Exit criteria
- Alerts trigger correctly; successful restore to staging documented with timings; no secrets in logs; TLS enabled.

Phase 10: Performance tuning, load tests, and production rollout (Week 10)
Objectives

- Achieve SLOs at target scale; production cutover with monitoring and rollback plan.
Tasks
- MLE/BE: Controlled backfill to 50k–100k papers and 10k+ repos in staging; measure index build times; tune HNSW ef_search and memory; VACUUM/ANALYZE.
- BE: Optimize slow queries; add missing indexes; ensure per_page caps; verify ETag savings in API.
- QA: Load tests at 50 RPS; check P95 latencies; fault-injection on workers; confirm graceful failure and retries.
- PM/TL: Go-live checklist; runbook finalization; on-call rotation; communication plan.
- SRE: Deploy to production; cron schedules enabled; watch metrics; canary rollback plan.
Deliverables
- Performance report and tuning changes; production deployment; monitoring dashboard handed to ops.
Exit criteria
- SLOs met or exceeded; error rates within thresholds; go-live signoff from PM/TL/SRE.

Execution details and cross-cutting concerns

Backlog by Epic (key stories)

- Infra/DevEx
  - Docker Compose for dev, Makefile, pre-commit, CI pipeline (build/lint/test).
  - K8s manifests (API Deployment/Service/Ingress; CronJobs for workers, backup).
- Database
  - Alembic migration with triggers and vector index fallback; downgrade script; test harness.
  - Seed and backfill utilities; EXPLAIN plan checks; ANALYZE after load.
- Ingestion: arXiv
  - Rate limit client; category iteration; PDF text extraction with fallbacks; embeddings; upsert idempotency; metrics and logs.
- Ingestion: GitHub
  - Search queries with budget; ETag/If-None-Match; repo enrichment; velocity score; upsert idempotency; metrics and logs.
- Embeddings and Vector search
  - Model loading and caching; embedding normalization; HNSW index; /papers/near endpoint; similarity scoring in response.
- Scoring and normalization
  - Six metrics implementations; domain metrics calculation; clipping and mapping; composite score; evidence tracking.
- Linking
  - Heuristics; README fetch and cache; confidence and evidence; dedupe; metrics.
- Opportunities
  - Weekly freeze logic; top-K selection; dedupe; narrative templating; endpoint.
- Observability and Ops
  - JSON logging, Prometheus metrics; dashboards; alerts; backup and restore; security hardening; rate limiting and TLS.

Dependencies and sequencing

- DB migrations before ingestion and API.
- Shared libs before workers.
- arXiv ingestion and embeddings before vector search and scoring.
- GitHub ingestion before linking and attention normalization.
- Scoring before opportunities generation.
- Observability before production go-live.

Definition of Done by area

- API
  - Unit and integration tests passing; OpenAPI updated; ETag and gzip verified; P95 latencies in staging within SLO; logs and metrics present.
- Workers
  - Idempotent upserts; rate-limit compliance; retries with jitter; metrics for requests/records/errors; failure of a single item doesn’t fail batch.
- Data
  - Scores in [0,1]; nullability constraints respected; domain_metrics present and <48h old; indexes in use; VACUUM/ANALYZE after large writes.
- Security and Ops
  - Secrets externalized; TLS in prod; backups functioning; restore tested; alerts firing; runbooks current.

Test strategy

- Unit tests: scoring math, embedding dimension check, HTTP client ETag and backoff, keyword/domain classification rules.
- Integration tests: migrations up/down, TSV trigger, vector similarity, API ETag 304, ingestion idempotency.
- End-to-end: ingest small slice, score, link, generate opportunities, API returns expected top entries.
- Load tests: 50k papers dataset; test /papers and /papers/near at 50 RPS; confirm P95s.
- Chaos/fault: GitHub 403 rate-limit simulation; PDF extraction errors; DB failover or restarts; ensure graceful recovery.

Performance plan

- Seed 50k papers progressively; measure HNSW build time; set ef_search to meet P95 < 500 ms; switch to IVFFLAT if memory constrained and validate accuracy.
- Add BRIN on time fields; ensure GIN on tsv/JSONB/arrays; limit select lists; set sensible per_page caps.
- Apply ANALYZE after initial loads and large batch updates.

Security and compliance

- GitHub token minimal scopes; periodic rotation.
- Database not publicly accessible; network policies enforce namespace isolation.
- Input validation and sanitization for API; logs scrubbed; no secrets in evidence fields.
- Weekly dependency vulnerability scan; pin versions.

Data backfill strategy

- Staging: 7–30 days backfill first; monitor rate limits and job durations; pause/resume capable.
- Production: staggered backfill by domain/category; watch DB bloat; run VACUUM and reindex if needed; temporarily increase HNSW ef_construction if rebuilding indexes.

Resourcing and estimates (person-weeks)

- TL: 4–5 pw across 10 weeks (architecture, reviews, tuning).
- BE: 8–10 pw (API, workers, DB, linking, opportunities).
- MLE: 5–6 pw (embeddings, scoring, normalization, narrative templates).
- SRE: 5–6 pw (CI/CD, K8s, observability, security, backups, rollout).
- QA: 3–4 pw (test plans, automation, load/perf, chaos).
These can overlap; total calendar duration ~10 weeks with 4–5 people part-time on multiple tracks.

Risks and mitigations

- External API limits: aggressive ETag usage; strict budgets; exponential backoff; alerting on 403s; schedule shifts to off-peak hours.
- PDF parsing failures: try/except per item; abstract fallback; capture error metrics.
- Model/embedding drift: dimension checks; embedding_model versioned; migration plan for model change.
- Query performance at scale: precomputed indexes, VACUUM/ANALYZE; tune HNSW ef_search; cap per_page; use EXPLAIN to guide fixes.
- Data quality drift: daily validation script; z-score clipping; manual spot checks on top opportunities; feedback loop.

Go-live checklist (gate to production)

- DB: schema applied; pgvector installed; indexes created; ANALYZE executed.
- Ingestion: arXiv and GitHub running in staging for 72 hours without critical alerts; rate-limit sleeps within expected bounds.
- Scoring: domain_metrics fresh; composite distribution healthy; evidence persisted.
- API: /healthz, /readyz, /metrics live; endpoints pass latency SLOs in staging; ETags working.
- Observability: Prometheus scraping; dashboards up; alerts tested.
- Backups: last 3 nightly backups verified; restore drill completed; runbook current.
- Security: TLS; secrets in vault/K8s; ingress rate limiting configured.
- Performance: load tests pass; vector search tuned; connection pooling configured.
- On-call: rotation set; incident playbooks published; rollback plan tested.

Post-launch plan (Weeks 11–12)

- Stabilization: monitor error budgets; triage issues; burn down performance and quality backlog.
- Quarterly restore drill scheduled; weekly vulnerability scan pipeline active.
- Phase 2 backlog grooming: add Semantic Scholar citations, patents/grants, auth, caching layer, read replicas.

Work tracking suggestions (Jira epics)

- EP-01 Infra and CI/CD
- EP-02 Database and Migrations
- EP-03 arXiv Ingestion
- EP-04 GitHub Ingestion
- EP-05 API v1 and Vector Search
- EP-06 Scoring and Normalization
- EP-07 Linking and Attention
- EP-08 Opportunities
- EP-09 Observability and Ops
- EP-10 Performance and Launch

If you want, I can turn this into a fully itemized Jira story list with estimates and dependencies, or generate the initial repo scaffolding and CI/CD workflows.
