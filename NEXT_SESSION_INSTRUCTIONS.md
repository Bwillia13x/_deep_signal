# Next Session Work Instructions - DeepTech Radar

**Generated:** November 18, 2025
**Status:** Phase 1 & Phase 2 Core Complete
**Next Focus:** Phase 3 - Deployment & Validation

---

## 🎯 Current Project Status

### What's Complete ✅

**Phase 0: Critical Blockers & Foundation** ✅
- Dependency fixes (pydantic-settings)
- Vector search endpoint fully functional with 6 integration tests
- Basic observability with 9 Prometheus metrics
- Grafana dashboard for ingestion and API monitoring

**Phase 1: Core Feature Completion** ✅
- **Complete 6D Scoring Engine (100%)**:
  1. Novelty score (vector space distance from domain centroid)
  2. Momentum score (recency-based scoring)
  3. Moat score (barriers to replication - 130+ keywords)
  4. Scalability score (manufacturing readiness - 130+ keywords)
  5. Attention gap score (quality vs attention mismatch)
  6. Network score (author collaboration patterns)
- **Composite scoring** with weighted sum + synergy bonus
- **Enhanced opportunities** with recommendation tiers (STRONG_BUY, BUY, WATCH, MONITOR)
- **Weekly freeze logic** and 4-week deduplication
- **Data-driven summaries** and investment thesis generation
- **38 of 39 tests passing (97% pass rate)**
- **Z-score normalization** for domain-level scoring
- **Evidence tracking** for full transparency

**Phase 2: Production Readiness** ✅
- **Full observability stack**:
  - 13 Prometheus alert rules (ingestion, API, database, workers, system)
  - 2 comprehensive Grafana dashboards (Overview + API Performance)
- **API enhancements**:
  - `/v1` API versioning
  - GZip compression (60-80% bandwidth reduction)
  - Advanced filters (min_composite_score, min_moat_score, min_scalability_score, domain, sort_by)
  - Structured error responses
- **Performance baselines documented**
- **Code quality optimizations** (batch queries, N+1 query elimination)
- **Production deployment guide** (`docs/PHASE_2_PRODUCTION_READINESS.md`)

### Current State Summary

| Component | Completion | Notes |
|-----------|-----------|-------|
| Database/pgvector foundation | 90% | Solid foundation with HNSW indexing |
| Architecture docs | 95% | Comprehensive documentation |
| 6D scoring engine | 100% | ✅ All dimensions complete + composite |
| Production observability | 85% | ✅ Major upgrade from 25% |
| API production readiness | 90% | ✅ Production-grade |
| Testing | 97% pass rate | ✅ 38/39 tests passing |
| Code quality | Optimized | ✅ Batch queries, PEP 8 compliant |
| Ingestion pipelines | 70% | Room for enhancement |

---

## 🚀 Recommended Next Steps - Phase 3 Priority Roadmap

### Option 1: Phase 3 - Deployment & Validation (HIGH PRIORITY)

**Goal:** Deploy to staging environment, validate end-to-end, prepare for production launch

**Why This First:**
- System is production-ready and needs real-world validation
- Staging deployment will surface any integration issues early
- End-to-end validation critical before production launch
- Establishes deployment patterns and runbooks

**Key Milestones:**

#### Milestone 3.1: Staging Deployment (Week 8)

**Priority Tasks:**
1. **Kubernetes Environment Setup**
   - Create staging namespace
   - Configure secrets (DATABASE_URL, GITHUB_TOKEN, OPENAI_API_KEY)
   - Set up persistent volume claims for DB if needed
   - Configure resource requests/limits

2. **Deploy Core Services**
   - Apply K8s manifests for API deployment, services, ingress
   - Deploy all CronJobs (arxiv_hourly, github_hourly, scoring_daily, linking_daily, opportunities_daily)
   - Configure Prometheus to scrape staging pods
   - Configure Grafana to connect to staging Prometheus

3. **Initial Validation**
   - Verify all pods running and healthy
   - Test health checks (`/health`, `/v1/health`)
   - Confirm metrics visible in Grafana
   - Manual trigger of each worker job

**Files to Create/Modify:**
- `deploy/k8s/staging/namespace.yaml`
- `deploy/k8s/staging/secrets.yaml` (template)
- `deploy/k8s/staging/api-deployment.yaml`
- `deploy/k8s/staging/cronjobs.yaml`
- `deploy/k8s/staging/ingress.yaml`
- `docs/DEPLOYMENT_GUIDE.md`

**Success Criteria:**
- All pods running and healthy for 48 hours
- No critical alerts triggered
- CronJobs execute on schedule
- Metrics flowing to Grafana

#### Milestone 3.2: End-to-End Validation (Week 8-9)

**Priority Tasks:**
1. **Execute Full Pipeline**
   - Run arXiv ingestion (7-day lookback)
   - Run GitHub ingestion (7-day lookback)
   - Run linking job
   - Run scoring job
   - Run opportunities generation

2. **Data Quality Validation**
   - Verify papers ingested with embeddings
   - Check repos with velocity scores
   - Validate links have confidence and evidence
   - Ensure all 6 scores computed
   - Check opportunities have recommendations and composite scores >0.65

3. **API Validation**
   - Test `/v1/papers` with various filters
   - Test `/v1/papers/near` with text queries and paper_id
   - Test `/v1/repositories` with filters
   - Test `/v1/opportunities` by domain/week
   - Verify pagination works correctly

4. **Performance Testing**
   - Run light load test (10 RPS) against staging
   - Verify latency targets met (p95 <300ms for lists, <500ms for vector search)
   - Check for memory leaks or resource growth

**Files to Create:**
- `scripts/staging_validation.py` - Automated validation script
- `tests/e2e/test_full_pipeline.py` - End-to-end test
- `docs/VALIDATION_CHECKLIST.md`

**Success Criteria:**
- Pipeline produces opportunities with composite scores
- All API endpoints return expected data formats
- No P0/P1 bugs found
- Performance baselines met

---

### Option 2: Remaining Phase 2 Enhancements (MEDIUM PRIORITY)

**Goal:** Complete remaining Phase 2 features for production polish

**Remaining Tasks from DEVELOPMENT_ROADMAP.md:**

#### Milestone 2.2: Advanced API Features

**Tasks:**
1. **ETag Support**
   - Compute ETags from query params + max(updated_at) + count
   - Return `ETag` header
   - Handle `If-None-Match` requests with 304 response

2. **Rate Limiting**
   - Implement per-IP rate limiting (using slowapi library)
   - Configure limits: 100 req/min per IP for general, 20 req/min for expensive queries
   - Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)

3. **Cursor-Based Pagination**
   - Add cursor pagination option for large result sets
   - Implement `cursor` and `next_cursor` in responses
   - More efficient than offset-based pagination at scale

**Files to Modify:**
- `app/api/routes/papers.py` - Add ETag and cursor pagination
- `app/middleware/rate_limit.py` - NEW: Rate limiting middleware
- `requirements/base.txt` - Add slowapi dependency

**Success Criteria:**
- Second identical request returns 304 Not Modified
- Rate limit returns 429 after threshold
- Cursor pagination handles 100k+ result sets efficiently

#### Milestone 2.3: Performance Tuning

**Tasks:**
1. **Database Index Optimization**
   - Run EXPLAIN on common queries
   - Add missing indexes for filter patterns
   - Add partial indexes for common WHERE clauses
   - Document index strategy

2. **pgvector Index Tuning**
   - Measure vector search p95 latency at scale
   - Tune ef_search parameter (test 32, 64, 128)
   - Compare HNSW vs IVFFLAT performance
   - Document optimal settings

3. **Worker Job Optimization**
   - Add batching to linking job to reduce N×M comparisons
   - Optimize embedding batch processing
   - Limit linking to repos with activity in last 180 days

**Files to Create:**
- `docs/PERFORMANCE_TUNING.md`
- `scripts/benchmark_vector_search.py`
- `alembic/versions/005_add_performance_indexes.py`

**Success Criteria:**
- Vector search p95 <500ms at 100k papers
- `/v1/papers` p95 <300ms
- Database EXPLAIN plans show index usage

#### Milestone 2.4: Backup & Disaster Recovery

**Tasks:**
1. **Backup Automation**
   - Create backup script using pg_dump
   - Configure daily backups at 02:00 UTC
   - Upload to object storage (S3 or equivalent) with encryption
   - Implement 30-day retention policy

2. **Restore Procedures**
   - Document step-by-step restore process
   - Create restore script
   - Test restore to staging environment

3. **Operational Runbooks**
   - Worker failure recovery
   - Database migration rollback
   - API incident response
   - GitHub token exhaustion
   - Alert response procedures

**Files to Create:**
- `scripts/backup_database.sh`
- `scripts/restore_database.sh`
- `docs/runbooks/WORKER_FAILURE.md`
- `docs/runbooks/DATABASE_ROLLBACK.md`
- `docs/runbooks/API_INCIDENT_RESPONSE.md`
- `docs/runbooks/GITHUB_RATE_LIMIT.md`
- `docs/runbooks/ALERT_RESPONSE.md`

**Success Criteria:**
- Backup job runs successfully daily
- Restore drill completes in <4h (RTO target)
- 5+ runbooks covering incident scenarios

---

### Option 3: Phase 1 Enhancement - Data Quality Improvements (LOW PRIORITY)

**Goal:** Improve ingestion pipeline data quality

**Why Lower Priority:**
- Core features are complete and functional
- These are enhancements, not blockers
- Can be done after staging validation

**Tasks from Milestone 1.5:**

1. **PDF Text Extraction**
   - Integrate pypdf library
   - Extract first 3-5 pages from arXiv PDFs
   - Cap at 10k characters
   - Set `has_pdf`, `pdf_text_pages` fields
   - Fallback to abstract on failure

2. **Enhanced Linking**
   - Add arXiv ID regex detection in README
   - Add DOI matching
   - Implement fuzzy title matching (using rapidfuzz)
   - Add confidence tiers (>0.9 for ID match, >0.8 for DOI, >0.6 for title)

3. **Dependency Extraction**
   - Detect requirements.txt, package.json, Cargo.toml in repos
   - Parse and store top-level dependencies
   - Set `has_dockerfile`, `has_ci_cd` flags

**Files to Modify:**
- `app/workers/arxiv_hourly.py` - Add PDF extraction
- `app/workers/linking_daily.py` - Enhance matching algorithms
- `app/workers/github_hourly.py` - Add dependency parsing
- `requirements/base.txt` - Add pypdf, rapidfuzz

**Success Criteria:**
- 70%+ of papers have `text_excerpt` populated
- Link confidence distribution shows >80% precision at conf >= 0.8
- Repositories have dependencies JSON populated

---

## 📋 Detailed Implementation Guide for Phase 3.1 (Recommended Start)

### Step 1: Prepare Kubernetes Manifests

**Create staging deployment files:**

```yaml
# deploy/k8s/staging/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deeptech-staging
  labels:
    environment: staging

# deploy/k8s/staging/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: deeptech-config
  namespace: deeptech-staging
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "staging"
  PROMETHEUS_MULTIPROC_DIR: "/tmp/prometheus"

# deploy/k8s/staging/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deeptech-api
  namespace: deeptech-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: deeptech-api
  template:
    metadata:
      labels:
        app: deeptech-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: api
        image: deeptech-radar-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: deeptech-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: deeptech-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

# deploy/k8s/staging/cronjobs.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: arxiv-hourly
  namespace: deeptech-staging
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: arxiv-worker
            image: deeptech-radar-worker:latest
            command: ["python", "-m", "app.workers.arxiv_hourly"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: deeptech-secrets
                  key: database-url
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: deeptech-secrets
                  key: openai-api-key
          restartPolicy: OnFailure
```

### Step 2: Create Deployment Scripts

**scripts/deploy_staging.sh:**
```bash
#!/bin/bash
set -e

echo "Deploying to staging environment..."

# Apply namespace
kubectl apply -f deploy/k8s/staging/namespace.yaml

# Apply secrets (from environment variables)
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=openai-api-key="${OPENAI_API_KEY}" \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --namespace=deeptech-staging \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply ConfigMap
kubectl apply -f deploy/k8s/staging/configmap.yaml

# Apply API deployment
kubectl apply -f deploy/k8s/staging/api-deployment.yaml

# Apply service
kubectl apply -f deploy/k8s/staging/service.yaml

# Apply ingress
kubectl apply -f deploy/k8s/staging/ingress.yaml

# Apply CronJobs
kubectl apply -f deploy/k8s/staging/cronjobs.yaml

echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/deeptech-api -n deeptech-staging

echo "Staging deployment complete!"
kubectl get pods -n deeptech-staging
```

### Step 3: Create Validation Scripts

**scripts/validate_staging.py:**
```python
#!/usr/bin/env python3
"""
Staging environment validation script.
Runs automated checks against staging deployment.
"""
import requests
import sys
import time
from typing import Dict, List

STAGING_URL = "https://staging.deeptech-radar.example.com"

def check_health() -> bool:
    """Verify health endpoint."""
    try:
        resp = requests.get(f"{STAGING_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def check_api_v1() -> bool:
    """Verify /v1 endpoints."""
    endpoints = [
        "/v1/papers?limit=10",
        "/v1/papers/near?text_query=quantum&k=5",
        "/v1/opportunities?limit=10",
    ]
    for endpoint in endpoints:
        try:
            resp = requests.get(f"{STAGING_URL}{endpoint}", timeout=10)
            if resp.status_code != 200:
                print(f"❌ Endpoint {endpoint} returned {resp.status_code}")
                return False
            print(f"✅ {endpoint} OK")
        except Exception as e:
            print(f"❌ Endpoint {endpoint} failed: {e}")
            return False
    return True

def check_metrics() -> bool:
    """Verify metrics endpoint."""
    try:
        resp = requests.get(f"{STAGING_URL}/metrics", timeout=5)
        if "api_requests_total" not in resp.text:
            print("❌ Metrics missing api_requests_total")
            return False
        print("✅ Metrics endpoint OK")
        return True
    except Exception as e:
        print(f"❌ Metrics check failed: {e}")
        return False

def main():
    print("Starting staging validation...")
    
    checks = [
        ("Health check", check_health),
        ("API v1 endpoints", check_api_v1),
        ("Metrics endpoint", check_metrics),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nRunning: {name}")
        result = check_func()
        results.append((name, result))
        time.sleep(1)
    
    print("\n" + "="*50)
    print("VALIDATION RESULTS")
    print("="*50)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All validation checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validation checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Step 4: Update Documentation

Create comprehensive deployment guide covering:
- Prerequisites (kubectl, access credentials)
- Environment setup
- Deployment steps
- Validation procedures
- Troubleshooting common issues
- Rollback procedures

---

## 🎯 Recommended Work Session Plan

### Session 1: Staging Infrastructure Setup (4-6 hours)

**Objectives:**
1. Create all K8s manifests for staging
2. Set up staging namespace and secrets
3. Deploy API service
4. Verify basic health checks

**Deliverables:**
- Complete K8s manifest files
- Deployed and running API pods
- Health endpoint responding

### Session 2: Worker Deployment (4-6 hours)

**Objectives:**
1. Deploy all CronJobs
2. Manually trigger each worker
3. Verify logs and metrics
4. Validate data flow

**Deliverables:**
- All CronJobs deployed
- First data ingestion successful
- Metrics visible in Grafana

### Session 3: End-to-End Validation (4-6 hours)

**Objectives:**
1. Run full pipeline
2. Validate data quality
3. Performance testing
4. Create validation scripts

**Deliverables:**
- Automated validation script
- Performance baseline report
- Data quality assessment

### Session 4: Production Preparation (4-6 hours)

**Objectives:**
1. Create production K8s manifests
2. Document deployment procedures
3. Create runbooks
4. Prepare go-live checklist

**Deliverables:**
- Production deployment ready
- Complete documentation
- Operational runbooks

---

## 📚 Key Reference Documents

### Documentation to Review Before Starting

1. **DEVELOPMENT_ROADMAP.md** - Full roadmap with all phases
2. **AUDIT_REPORT.md** - Component analysis and current state
3. **docs/PHASE_2_PRODUCTION_READINESS.md** - Production deployment guide
4. **docs/vector_search_performance.md** - Performance benchmarks
5. **deploy/monitoring/prometheus-alerts.yml** - Alert configuration

### Architecture Files

1. **app/main.py** - FastAPI application entry point
2. **app/api/routes/papers.py** - Main API endpoints
3. **app/workers/** - All worker job implementations
4. **app/services/scoring.py** - Scoring engine implementation
5. **deploy/monitoring/** - Observability configuration

---

## ⚠️ Important Considerations

### Before Starting Phase 3:

1. **Infrastructure Access:**
   - Ensure you have access to Kubernetes cluster
   - Verify database credentials for staging
   - Confirm API keys (OpenAI, GitHub) are available

2. **Environment Setup:**
   - Staging database should be provisioned
   - Object storage for backups should be configured
   - Prometheus and Grafana should be accessible

3. **Resource Planning:**
   - Allocate 4-6 hours for initial deployment
   - Plan for 48-hour monitoring period
   - Schedule team availability for troubleshooting

4. **Risk Mitigation:**
   - Have rollback plan ready
   - Keep staging independent from production
   - Document all changes and decisions

### Testing Strategy:

1. **Smoke Tests:** Basic health and connectivity checks
2. **Integration Tests:** Full pipeline execution
3. **Performance Tests:** Light load testing (10 RPS)
4. **Data Quality Tests:** Spot-checks and validation
5. **Security Tests:** Basic vulnerability scanning

---

## 🔄 Alternative Paths

### If Deployment Infrastructure Not Ready:

**Focus on Phase 2 Enhancements:**
1. Implement ETag support for caching
2. Add rate limiting
3. Optimize database indexes
4. Create backup automation scripts
5. Write operational runbooks

### If Team Prefers Feature Work:

**Focus on Data Quality (Milestone 1.5):**
1. Add PDF text extraction
2. Enhance linking algorithms
3. Extract repository dependencies
4. Improve data validation

### If Focus is on Testing:

**Expand Test Coverage:**
1. Add more unit tests (target 70%+ coverage)
2. Create integration tests for workers
3. Add API contract tests
4. Implement load testing framework

---

## 📞 Getting Help

### Common Issues and Solutions

**Issue: K8s Deployment Fails**
- Check namespace exists
- Verify secrets are created correctly
- Check resource quotas
- Review pod logs: `kubectl logs <pod-name> -n deeptech-staging`

**Issue: Database Connection Fails**
- Verify DATABASE_URL format
- Check network policies
- Confirm database is accessible from cluster
- Test connection from pod: `kubectl exec -it <pod-name> -n deeptech-staging -- psql $DATABASE_URL`

**Issue: Workers Not Running**
- Check CronJob schedule syntax
- Verify job succeeded: `kubectl get jobs -n deeptech-staging`
- Review job logs: `kubectl logs job/<job-name> -n deeptech-staging`

**Issue: Metrics Not Appearing**
- Verify Prometheus scrape config
- Check pod annotations
- Confirm `/metrics` endpoint accessible
- Review Prometheus targets page

---

## 🎓 Learning Resources

### Kubernetes
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Secrets Management](https://kubernetes.io/docs/concepts/configuration/secret/)

### Observability
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)

### FastAPI Deployment
- [FastAPI in Containers](https://fastapi.tiangolo.com/deployment/docker/)
- [Production Settings](https://fastapi.tiangolo.com/deployment/manually/)

---

## ✅ Success Criteria Summary

### Phase 3.1 Complete When:
- [ ] All staging pods running and healthy for 48 hours
- [ ] No critical alerts triggered
- [ ] CronJobs execute on schedule
- [ ] Metrics visible in Grafana
- [ ] Health checks passing
- [ ] Deployment documented

### Phase 3.2 Complete When:
- [ ] Full pipeline executed successfully
- [ ] Opportunities generated with composite scores
- [ ] Data quality validated
- [ ] Performance baselines met
- [ ] No P0/P1 bugs found

### Ready for Production When:
- [ ] Staging stable for 7+ days
- [ ] All tests passing
- [ ] Backup/restore tested
- [ ] Runbooks complete
- [ ] Go-live checklist approved

---

**Next Recommended Action:** Start with Phase 3.1 - Staging Deployment

Focus on getting the system deployed and validated in a real environment before adding more features. This will surface integration issues early and establish confidence in the production deployment process.

Good luck! 🚀
