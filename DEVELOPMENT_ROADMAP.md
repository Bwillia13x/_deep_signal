# DeepTech Radar - Phased Development Roadmap

**Version:** 1.0
**Date:** November 18, 2025
**Status:** Active Development Plan

---

## Overview

This roadmap provides a systematic, phased approach to bringing the DeepTech Radar project from its current **55-60% completion** state to **full production readiness**. The plan is divided into 4 major phases spanning approximately **12 weeks** with clear milestones and deliverables.

---

## Current State Summary

**Starting Point:**
- ✅ Architecture & Planning: 95% complete
- ✅ Database Schema: 90% complete
- 🟡 Ingestion Pipelines: 60-75% complete
- 🔴 Scoring Engine: 35% complete
- 🔴 Observability: 25% complete
- 🔴 Testing: 15% complete

**Target End State:**
- 🎯 MVP Feature Complete: 100%
- 🎯 Production Ready: 95%+
- 🎯 Test Coverage: 70%+
- 🎯 Observability: 100%
- 🎯 Documentation: 100%

---

## Phase 0: Critical Blockers & Foundation (Week 1)

**Goal:** Fix critical blockers preventing builds/tests and establish baseline functionality

### Milestone 0.1: Dependency & Build Fix (Days 1-2)

**Tasks:**
- [ ] Add `pydantic-settings>=2.0.0` to `requirements/base.txt`
- [ ] Verify all dependencies resolve correctly
- [ ] Run `make setup` successfully
- [ ] Fix any import/dependency conflicts
- [ ] Validate `make test` runs (even if tests fail)

**Deliverables:**
- Working development environment
- Green CI build pipeline
- All tests discoverable and executable

**Acceptance Criteria:**
- `make setup && make test` completes without import errors
- CI pipeline passes lint and type checking
- Docker-compose stack starts successfully

### Milestone 0.2: Vector Search Completion (Days 3-5)

**Tasks:**
- [ ] Complete `/papers/near` endpoint implementation
- [ ] Add text query embedding in endpoint
- [ ] Add paper_id lookup and embedding retrieval
- [ ] Implement pgvector similarity query with ef_search tuning
- [ ] Add similarity scores to response
- [ ] Write integration test for vector search
- [ ] Document query performance characteristics

**Deliverables:**
- Functional vector search endpoint
- Tests validating search results
- Performance baseline (p95 < 500ms target)

**Acceptance Criteria:**
- `/papers/near?text_query=quantum computing&k=10` returns results
- `/papers/near?paper_id=123&k=20` returns similar papers
- Integration test validates similarity ordering

### Milestone 0.3: Basic Observability (Days 5-7)

**Tasks:**
- [ ] Add Prometheus metrics to arXiv worker:
  - `ingest_arxiv_requests_total`
  - `ingest_arxiv_papers_processed_total`
  - `ingest_arxiv_errors_total`
- [ ] Add Prometheus metrics to GitHub worker:
  - `ingest_github_requests_total`
  - `ingest_github_repos_processed_total`
  - `ingest_github_rate_limit_hits_total`
- [ ] Add API request metrics:
  - `api_requests_total{method, endpoint, status}`
  - `api_request_duration_seconds{method, endpoint}`
- [ ] Verify metrics appear in Prometheus UI
- [ ] Create simple Grafana dashboard JSON with basic panels

**Deliverables:**
- Instrumented workers with key metrics
- API request tracking
- Basic Grafana dashboard (ingestion overview)

**Acceptance Criteria:**
- Prometheus scrapes metrics from API and workers
- Grafana displays at least 4 panels (requests, papers/hour, errors, latency)

**Exit Criteria for Phase 0:**
- ✅ All builds green
- ✅ Vector search functional
- ✅ Basic metrics visible
- ✅ No P0 blockers remaining

---

## Phase 1: Core Feature Completion (Weeks 2-4)

**Goal:** Complete scoring engine, improve data quality, expand test coverage

### Milestone 1.1: Scoring Engine - Moat & Scalability (Week 2)

**Tasks:**
- [ ] Implement moat score calculation:
  - Equipment barrier detection (keywords: cleanroom, cryogenic, vacuum, etc.)
  - Process barrier detection (manual assembly, specialized equipment)
  - Material barrier detection (rare earth, toxic, controlled substances)
  - Compute barrier detection (GPU clusters, supercomputer, quantum)
  - Code/data availability penalty/bonus
- [ ] Create configurable lexicons for barriers (JSON or YAML config)
- [ ] Implement scalability score calculation:
  - Manufacturing-friendly signals (CMOS, wafer-scale, room-temp, etc.)
  - Economic signals (yield, cost mentions, pilot line)
  - Maturity signals (TRL levels, licensing, pilot)
  - Blocker detection (cleanroom-only, manual, regulatory)
- [ ] Store evidence JSON for both metrics
- [ ] Add domain normalization via z-score clipping
- [ ] Write unit tests for pattern matching and scoring
- [ ] Update `scoring_daily.py` to compute and persist moat/scalability

**Deliverables:**
- Moat score: 0-1 with evidence
- Scalability score: 0-1 with evidence
- Configurable barrier/signal lexicons
- 15+ unit tests for scoring logic

**Acceptance Criteria:**
- Papers have `moat_score`, `scalability_score`, `moat_evidence`, `scalability_evidence`
- Scores in [0, 1] range
- Domain normalization applied
- Tests validate lexicon matching

### Milestone 1.2: Scoring Engine - Attention Gap & Network (Week 2-3)

**Tasks:**
- [ ] Implement attention_gap score:
  - Calculate technical quality proxy (avg of moat + scalability)
  - Calculate attention proxy (repo stars + link count, domain-normalized)
  - Compute gap: `1 - normalized_attention` weighted by quality
- [ ] Implement network score:
  - Extract co-author relationships from papers
  - Compute degree/centrality per author per domain (NetworkX or SQL)
  - Average author centrality for each paper
  - Add cross-domain collaboration bonus
  - Domain-normalize final score
- [ ] Add domain metrics tracking for attention and network
- [ ] Write unit tests for network calculations
- [ ] Update opportunities to use all component scores

**Deliverables:**
- Attention gap score with evidence
- Network score with co-author graph
- Updated domain_metrics table with attention/network stats
- 10+ unit tests

**Acceptance Criteria:**
- All 6 scores computed: novelty, momentum, moat, scalability, attention_gap, network
- Composite score formula applies weights and synergy bonus
- Papers table has complete scoring data

### Milestone 1.3: Composite Scoring & Opportunities Enhancement (Week 3)

**Tasks:**
- [ ] Implement composite score calculation:
  - Weighted sum: novelty(0.25) + momentum(0.15) + attention_gap(0.20) + moat(0.20) + scalability(0.15) + network(0.05)
  - Add synergy bonus: +0.02 per metric >0.7, capped at +0.08
  - Clip to [0, 1]
- [ ] Store `composite_score` and `scoring_metadata` in papers table
- [ ] Update opportunities_daily.py:
  - Use composite score for ranking
  - Apply threshold filtering (min_score >= 0.65)
  - Implement weekly freeze logic (Monday 00:00 UTC)
  - Add 4-week deduplication (exclude papers selected in last 4 weeks)
  - Generate recommendation tiers (STRONG_BUY >0.8, BUY >0.7, WATCH >0.6)
  - Populate strengths/risks/comparables from evidence
  - Improve executive summary template with data-driven insights
- [ ] Add integration test for end-to-end scoring pipeline

**Deliverables:**
- Composite scoring functional
- Enhanced opportunities with tiers and narratives
- Weekly freeze and deduplication working

**Acceptance Criteria:**
- Opportunities have recommendation field
- Top opportunities have composite_score >0.65
- Weekly deduplication prevents repeats
- Integration test validates scoring → opportunities flow

### Milestone 1.4: Test Coverage Expansion (Week 3-4)

**Tasks:**
- [ ] Add unit tests for all scoring functions (target: 20 tests)
- [ ] Add integration tests for:
  - arXiv ingestion end-to-end
  - GitHub ingestion end-to-end
  - Linking job execution
  - Scoring pipeline execution
  - Opportunities generation
- [ ] Add API contract tests:
  - `/papers` with various filters
  - `/papers/near` with text and paper_id
  - `/repositories` with filters
  - `/opportunities` with domain/week filtering
- [ ] Add migration tests (upgrade/downgrade)
- [ ] Create test fixtures for deterministic data
- [ ] Configure pytest-cov for coverage reporting
- [ ] Target: 60% overall coverage

**Deliverables:**
- 50+ total tests
- Coverage report showing 60%+ coverage
- CI enforcing test passage

**Acceptance Criteria:**
- `make test` shows 60%+ coverage
- All critical paths have tests
- CI fails on test failures

### Milestone 1.5: Data Quality Improvements (Week 4)

**Tasks:**
- [ ] Add PDF text extraction to arXiv worker:
  - Integrate pypdf library
  - Extract first 3-5 pages
  - Cap at 10k characters
  - Set `has_pdf`, `pdf_text_pages` fields
  - Fallback to abstract on failure
- [ ] Enhance linking job:
  - Add arXiv ID regex detection in README (fetch via GitHub API)
  - Add DOI matching
  - Implement fuzzy title matching (fuzzywuzzy or rapidfuzz)
  - Add confidence tiers (>0.9 for ID match, >0.8 for DOI, >0.6 for title)
- [ ] Add dependency manifest extraction to GitHub worker (best-effort):
  - Detect requirements.txt, package.json, Cargo.toml
  - Parse and store top-level dependencies
  - Set `has_dockerfile`, `has_ci_cd` flags
- [ ] Add error metrics and logging for each worker

**Deliverables:**
- Papers with `text_excerpt` populated
- Higher quality paper-repo links
- Repository enrichment with dependencies

**Acceptance Criteria:**
- 70%+ of papers have `text_excerpt` or fallback
- Link confidence distribution shows >80% precision at conf >= 0.8
- Repositories have dependencies JSON populated

**Exit Criteria for Phase 1:**
- ✅ All 6 scoring dimensions implemented
- ✅ Test coverage ≥60%
- ✅ Composite scoring functional
- ✅ Data quality significantly improved

---

## Phase 2: Production Readiness (Weeks 5-7)

**Goal:** Observability, performance tuning, API enhancements, deployment preparation

### Milestone 2.1: Full Observability Stack (Week 5)

**Tasks:**
- [ ] Complete Prometheus metrics instrumentation:
  - Add all metrics from architecture spec
  - Add histograms for durations (API, DB queries, embeddings)
  - Add rate limit sleep counters per service
- [ ] Create comprehensive Grafana dashboards:
  - **Ingestion Dashboard:** requests/hour, success rate, papers/repos ingested, errors by source
  - **API Dashboard:** request rate, p50/p95/p99 latency, error rate, top endpoints
  - **Scoring Dashboard:** job duration, domain metrics freshness, score distributions
  - **System Dashboard:** DB connections, memory, CPU (if available)
- [ ] Define Prometheus alert rules:
  - No papers ingested in 24h
  - GitHub 403 rate >20% in 1h
  - API 5xx >1% for 5m
  - Vector search p95 >1s for 15m
  - Scoring job failed
  - DB connection errors
- [ ] Configure alertmanager (if using) or document Slack/PagerDuty integration
- [ ] Add structured JSON logging throughout:
  - Include request_id, component, severity
  - Sanitize secrets from logs
  - Add log sampling for high-volume messages

**Deliverables:**
- 4 Grafana dashboards (JSON in repo)
- 8+ alert rules configured
- Full metrics coverage across all components
- Structured logging with trace IDs

**Acceptance Criteria:**
- Dashboards display live data
- Alerts can be triggered via test scenarios
- Logs are parseable JSON with consistent schema

### Milestone 2.2: API Enhancements (Week 5-6)

**Tasks:**
- [ ] Implement ETag support:
  - Compute ETags from query params + max(updated_at) + count
  - Return `ETag` header
  - Handle `If-None-Match` requests with 304 response
- [ ] Add response compression:
  - Enable gzip for responses >1KB
  - Configure middleware in FastAPI
- [ ] Add rate limiting:
  - Implement per-IP rate limiting (slowapi or custom)
  - Configure limits: 100 req/min per IP for general, 20 req/min for expensive queries
- [ ] Add advanced filters to `/papers`:
  - `min_moat`, `min_scalability`, `min_composite_score`
  - Sort by `composite` when available
- [ ] Add cursor-based pagination option for large result sets
- [ ] Add `/v1` versioning prefix to all endpoints
- [ ] Improve error responses with structured error JSON

**Deliverables:**
- ETag caching functional
- Gzip compression enabled
- Rate limiting active
- API versioned as /v1

**Acceptance Criteria:**
- Second identical request returns 304 Not Modified
- Large responses are gzip-compressed
- Rate limit returns 429 after threshold
- All endpoints under /v1

### Milestone 2.3: Performance Tuning & Validation (Week 6-7)

**Tasks:**
- [ ] Backfill staging database:
  - Seed 50k-100k papers across categories
  - Seed 10k+ repositories
  - Run linking and scoring jobs
- [ ] VACUUM ANALYZE database after backfill
- [ ] Validate and tune pgvector index:
  - Measure vector search p95 latency
  - Tune ef_search parameter (start at 64, test 32-128)
  - Document optimal settings
  - Verify HNSW vs IVFFLAT performance
- [ ] Add missing indexes identified via EXPLAIN:
  - Review slow queries
  - Add indexes for common filter patterns
  - Add partial indexes where appropriate
- [ ] Optimize linking job:
  - Add batching to reduce N×M comparisons
  - Consider adding a linking candidates cache
  - Limit to repos with activity in last 180 days
- [ ] Run load tests:
  - Simulate 50 RPS on `/papers` and `/papers/near`
  - Validate p95 latency targets (<300ms list, <500ms vector search)
  - Identify bottlenecks
- [ ] Document performance baselines and tuning parameters

**Deliverables:**
- Performance report with baselines
- Tuned database and indexes
- Load test results
- Optimized worker jobs

**Acceptance Criteria:**
- Vector search p95 <500ms at 100k papers
- `/papers` p95 <300ms
- Database EXPLAIN plans show index usage
- Load tests pass at 50 RPS

### Milestone 2.4: Backup & Disaster Recovery (Week 7)

**Tasks:**
- [ ] Implement backup automation:
  - Create backup script using pg_dump
  - Configure daily backups at 02:00 UTC
  - Upload to object storage (S3 or equivalent) with encryption
  - Implement 30-day retention policy
- [ ] Create restore procedure:
  - Document step-by-step restore process
  - Create restore script
  - Test restore to staging environment
- [ ] Conduct restore drill:
  - Perform full restore to clean database
  - Verify data integrity
  - Document RTO and RPO achieved
- [ ] Create runbooks:
  - Worker failure recovery
  - Database migration rollback
  - API incident response
  - GitHub token exhaustion
  - Alert response procedures

**Deliverables:**
- Automated daily backups
- Restore runbook tested
- 5+ operational runbooks

**Acceptance Criteria:**
- Backup job runs successfully daily
- Restore drill completes in <4h (RTO target)
- Runbooks cover 5+ incident scenarios

**Exit Criteria for Phase 2:**
- ✅ Full observability operational
- ✅ API production-ready with caching/compression/rate limiting
- ✅ Performance validated at scale
- ✅ Backup/restore tested
- ✅ Runbooks documented

---

## Phase 3: Deployment & Validation (Weeks 8-10)

**Goal:** Deploy to staging, validate end-to-end, prepare for production launch

### Milestone 3.1: Staging Deployment (Week 8)

**Tasks:**
- [ ] Prepare Kubernetes environment:
  - Create staging namespace
  - Configure secrets (DATABASE_URL, GITHUB_TOKEN)
  - Set up persistent volume claims for DB if needed
- [ ] Deploy to staging:
  - Apply all K8s manifests (API deployment, services, ingress)
  - Deploy all CronJobs (arxiv, github, scoring, linking, opportunities)
  - Configure Prometheus to scrape staging
  - Configure Grafana to connect to staging Prometheus
- [ ] Validate deployment:
  - All pods running and healthy
  - Health checks passing
  - Metrics visible in Grafana
- [ ] Run staging smoke tests:
  - API endpoints respond correctly
  - Manual trigger of each worker job
  - Verify data flows through pipeline
- [ ] Monitor staging for 48 hours:
  - Watch for errors, crashes, resource issues
  - Validate CronJob schedules
  - Check log volume and disk usage

**Deliverables:**
- Fully deployed staging environment
- All services healthy
- 48-hour stability period

**Acceptance Criteria:**
- Zero deployment errors
- All health checks green
- CronJobs execute on schedule
- No critical alerts in 48h

### Milestone 3.2: End-to-End Validation (Week 8-9)

**Tasks:**
- [ ] Execute full pipeline in staging:
  - Run arXiv ingestion (7-day lookback)
  - Run GitHub ingestion (7-day lookback)
  - Run linking job
  - Run scoring job
  - Run opportunities generation
- [ ] Validate data quality:
  - Verify papers ingested with embeddings
  - Check repos with velocity scores
  - Validate links have confidence and evidence
  - Ensure all 6 scores computed
  - Check opportunities have recommendations
- [ ] Validate API responses:
  - Query papers with various filters
  - Test vector search with sample queries
  - Retrieve opportunities by domain and week
  - Verify pagination works correctly
- [ ] Performance validation:
  - Run light load test (10 RPS) against staging
  - Verify latency targets met
  - Check for memory leaks or resource growth
- [ ] Security validation:
  - Verify secrets not in logs
  - Check API has no SQL injection vulnerabilities (basic sqlmap scan)
  - Validate CORS configuration
  - Test rate limiting

**Deliverables:**
- End-to-end pipeline validated
- Data quality spot-checks passed
- Performance baselines confirmed
- Security scan clean

**Acceptance Criteria:**
- Pipeline produces opportunities with composite scores >0.65
- API returns expected data format
- No P0/P1 bugs found
- Security scan shows no critical issues

### Milestone 3.3: Production Preparation (Week 9-10)

**Tasks:**
- [ ] Production environment setup:
  - Create production namespace in K8s
  - Configure production secrets
  - Set up production database (managed PostgreSQL recommended)
  - Configure TLS/SSL certificates for ingress
  - Set up production Prometheus and Grafana
- [ ] Production configuration:
  - Tune resource requests/limits for pods
  - Configure horizontal pod autoscaling (HPA) for API
  - Set production-grade DB connection pool sizes
  - Configure backup retention and monitoring
  - Set up log aggregation (if available)
- [ ] Pre-launch checklist:
  - [ ] All tests passing in CI
  - [ ] Staging stable for 7+ days
  - [ ] Backup automation tested
  - [ ] Runbooks reviewed and approved
  - [ ] Dashboards and alerts configured
  - [ ] On-call rotation established
  - [ ] Rollback plan documented
  - [ ] Incident response process defined
- [ ] Documentation updates:
  - Update README with production URLs
  - Document API usage with examples
  - Create operator's guide
  - Document configuration options
  - Add troubleshooting guide

**Deliverables:**
- Production environment ready
- Pre-launch checklist complete
- Comprehensive documentation

**Acceptance Criteria:**
- All checklist items verified
- Production environment mirrors staging
- Documentation reviewed and approved

### Milestone 3.4: Production Launch (Week 10)

**Tasks:**
- [ ] Deploy to production:
  - Apply K8s manifests to production
  - Deploy API and workers
  - Enable CronJobs with conservative schedules
- [ ] Smoke test production:
  - Verify health endpoints
  - Test each API endpoint manually
  - Check metrics appear in Grafana
- [ ] Initial data ingestion:
  - Run arXiv worker (1-day lookback first)
  - Run GitHub worker (1-day lookback first)
  - Monitor logs and metrics closely
  - Gradually increase lookback if successful
- [ ] Monitor for 24 hours:
  - Watch error rates
  - Check resource usage
  - Validate data quality
  - Respond to any alerts
- [ ] Gradual scale-up:
  - Increase lookback to 7 days
  - Increase lookback to 30 days
  - Enable all CronJobs on full schedule
  - Run first full scoring and opportunities cycle
- [ ] Post-launch validation:
  - Verify opportunities generated
  - Spot-check data quality
  - Confirm SLOs met
  - Gather initial user feedback (if applicable)

**Deliverables:**
- Production deployment live
- Initial data ingested
- 24h monitoring period clean
- First opportunities generated

**Acceptance Criteria:**
- Production stable for 72h
- API availability >99.5%
- Opportunities generated successfully
- No critical incidents

**Exit Criteria for Phase 3:**
- ✅ Production deployed and stable
- ✅ Full pipeline operational
- ✅ SLOs met or exceeded
- ✅ Monitoring and alerting active

---

## Phase 4: Stabilization & Phase 2 Planning (Weeks 11-12)

**Goal:** Stabilize production, address technical debt, plan Phase 2 enhancements

### Milestone 4.1: Production Stabilization (Week 11)

**Tasks:**
- [ ] Monitor and triage:
  - Review all alerts from first week
  - Identify and fix any performance issues
  - Address data quality anomalies
  - Tune resource allocations based on actual usage
- [ ] Performance optimization:
  - Optimize slow queries identified in production
  - Tune autoscaling thresholds
  - Adjust CronJob schedules to avoid resource contention
- [ ] Bug fixes:
  - Fix any issues discovered in production
  - Address edge cases in scoring or linking
  - Improve error messages and logging
- [ ] Documentation updates:
  - Document any production learnings
  - Update runbooks based on incidents
  - Add FAQ based on common issues

**Deliverables:**
- Issue backlog prioritized
- Critical bugs fixed
- Performance tuned

**Acceptance Criteria:**
- Production uptime >99.9%
- No P0/P1 issues in backlog
- Dashboards show healthy metrics

### Milestone 4.2: Technical Debt Reduction (Week 11-12)

**Tasks:**
- [ ] Increase test coverage to 70%+:
  - Add missing unit tests
  - Add edge case coverage
  - Improve integration tests
- [ ] Code quality improvements:
  - Refactor complex functions
  - Improve error handling consistency
  - Add docstrings to public functions
  - Run and fix all linter warnings
- [ ] Security hardening:
  - Add dependency vulnerability scanning to CI
  - Implement secrets scanning (e.g., truffleHog)
  - Add OWASP security headers to API
  - Document security best practices
- [ ] Performance improvements:
  - Optimize embedding batch processing
  - Add caching for frequent queries (if needed)
  - Optimize linking job algorithm

**Deliverables:**
- Test coverage ≥70%
- Security scanning in CI
- Code quality score improved

**Acceptance Criteria:**
- CI enforces security scans
- No high-severity vulnerabilities
- Test coverage report shows 70%+

### Milestone 4.3: Quarterly Review & Phase 2 Planning (Week 12)

**Tasks:**
- [ ] Conduct quarterly review:
  - Analyze usage patterns and metrics
  - Review opportunity quality and user feedback
  - Assess infrastructure costs
  - Document lessons learned
- [ ] Plan Phase 2 features (per architecture.md):
  - Semantic Scholar integration for citations
  - Patent and grant data sources
  - Advanced domain classification (spaCy/BERT)
  - Real-time alerting for opportunities
  - Authentication and authorization
  - Caching layer (Redis)
  - Read replicas for scaling
- [ ] Prioritize Phase 2 backlog:
  - Estimate effort for each feature
  - Identify dependencies
  - Sequence by value and effort
- [ ] Create Phase 2 roadmap:
  - Define milestones
  - Assign ownership
  - Set timeline (next 3-6 months)

**Deliverables:**
- Quarterly review report
- Phase 2 backlog prioritized
- Phase 2 roadmap (3-6 month plan)

**Acceptance Criteria:**
- Review presented to stakeholders
- Phase 2 priorities agreed upon
- Roadmap approved

**Exit Criteria for Phase 4:**
- ✅ Production stable and optimized
- ✅ Technical debt addressed
- ✅ Phase 2 roadmap defined
- ✅ MVP officially complete

---

## Success Metrics & KPIs

### Development Metrics
- **Code Coverage:** 15% → 70%+
- **Test Count:** 4 → 80+ tests
- **Build Success Rate:** 0% → 100%
- **Component Completion:** 55% → 100%

### Operational Metrics (Post-Launch)
- **API Availability:** >99.9% monthly
- **API p95 Latency:** <300ms for list, <500ms for vector search
- **Data Freshness:** Papers <24h old, opportunities <7 days
- **Error Rate:** <0.5% for ingestion, <1% for API

### Data Quality Metrics
- **Papers Ingested:** 0 → 50k+ (target 100k)
- **Repositories Linked:** 0 → 10k+
- **Link Precision:** Target >80% at confidence ≥0.8
- **Opportunities Generated:** Weekly, 5-20 per domain

### Business Metrics (Phase 2)
- **Opportunity Quality:** User feedback scoring
- **Discovery Rate:** Novel opportunities identified
- **Time to Market:** Research → opportunity detection time

---

## Risk Mitigation

### High-Priority Risks

**Risk 1: Scope Creep**
- **Mitigation:** Strict adherence to phase boundaries, defer Phase 2 features
- **Owner:** Tech Lead

**Risk 2: External API Rate Limits**
- **Mitigation:** Conservative batch sizes, ETag caching, backoff strategies
- **Owner:** Backend Engineer

**Risk 3: Performance Degradation at Scale**
- **Mitigation:** Early load testing, index tuning, query optimization
- **Owner:** DevOps/SRE

**Risk 4: Data Quality Issues**
- **Mitigation:** Validation tests, spot-checks, user feedback loop
- **Owner:** Data Engineer

**Risk 5: Resource/Time Constraints**
- **Mitigation:** Prioritize critical path, cut scope if needed, communicate early
- **Owner:** PM

---

## Resource Requirements

### Team Composition (Recommended)

**Full-Time (Weeks 1-10):**
- 1 Backend Engineer (API, workers, scoring)
- 1 Data/ML Engineer (embeddings, scoring algorithms)
- 0.5 DevOps/SRE (K8s, observability, backups)

**Part-Time (Weeks 1-10):**
- 0.5 Tech Lead (architecture, reviews, decisions)
- 0.3 QA Engineer (tests, validation)

**Total Effort:** ~3.3 FTE × 10 weeks = 33 person-weeks

### Infrastructure Requirements

**Development:**
- Local Docker-compose (no cost)

**Staging:**
- Managed PostgreSQL (2 vCPU, 8GB RAM): ~$100/month
- K8s cluster (3 nodes, 2 vCPU each): ~$150/month
- Object storage for backups: ~$10/month
- **Total:** ~$260/month

**Production:**
- Managed PostgreSQL (4 vCPU, 16GB RAM): ~$300/month
- K8s cluster (5 nodes, 4 vCPU each): ~$500/month
- Object storage for backups: ~$20/month
- **Total:** ~$820/month

**Estimated Total Cost (12 weeks):** ~$3,500 infrastructure + 33 person-weeks labor

---

## Go/No-Go Decision Points

### Phase 0 Exit Gate (Week 1)
- ✅ Build/test pipeline working
- ✅ Vector search functional
- ✅ Basic metrics visible
- **Decision:** Proceed to Phase 1 or address blockers

### Phase 1 Exit Gate (Week 4)
- ✅ All 6 scoring dimensions implemented
- ✅ Test coverage ≥60%
- ✅ Composite scoring validated
- **Decision:** Proceed to Phase 2 or iterate

### Phase 2 Exit Gate (Week 7)
- ✅ Observability complete
- ✅ Performance validated
- ✅ Backup/restore tested
- **Decision:** Proceed to staging deployment or fix issues

### Phase 3 Exit Gate (Week 10)
- ✅ Production deployed and stable
- ✅ SLOs met
- ✅ No critical issues
- **Decision:** Production launch or rollback

---

## Communication Plan

### Daily
- Standup (async or 15min sync)
- Blockers escalated immediately

### Weekly
- Sprint review/demo (Fridays)
- Metrics review
- Risk assessment update

### Milestone-Based
- Phase completion demo
- Stakeholder review
- Go/no-go decision meeting

### Incident-Driven
- Post-incident review (if applicable)
- Runbook updates

---

## Appendix: Quick Reference

### Critical Path Activities
1. Fix pydantic-settings dependency
2. Complete vector search endpoint
3. Implement all 6 scoring dimensions
4. Expand test coverage to 60%+
5. Build observability stack
6. Deploy to staging
7. Validate end-to-end
8. Deploy to production

### Dependencies
- Phase 1 requires Phase 0 complete
- Phase 2 performance tuning requires Phase 1 scoring complete
- Phase 3 deployment requires Phase 2 observability complete

### External Dependencies
- GitHub API access (token required)
- arXiv API (no auth, rate limited)
- Managed PostgreSQL (if using)
- Object storage (for backups)

---

## Conclusion

This phased roadmap provides a clear path from the current **55-60% complete** state to a **production-ready MVP** in approximately **12 weeks**. The plan prioritizes:

1. **Fixing critical blockers** (Week 1)
2. **Completing core features** (Weeks 2-4)
3. **Production readiness** (Weeks 5-7)
4. **Deployment and validation** (Weeks 8-10)
5. **Stabilization and planning** (Weeks 11-12)

By following this roadmap systematically, the DeepTech Radar project will achieve:
- ✅ Full feature completeness per architecture specification
- ✅ Production-grade reliability and observability
- ✅ Validated performance at scale
- ✅ Comprehensive testing and documentation
- ✅ Clear path to Phase 2 enhancements

**Next Step:** Begin Phase 0, Milestone 0.1 - Fix dependency issues and establish baseline functionality.

---

**Roadmap Version:** 1.0
**Last Updated:** November 18, 2025
**Status:** Active
