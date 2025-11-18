# DeepTech Radar - Validation Checklist

**Version:** 1.0  
**Environment:** Staging / Production  
**Date:** _____________  
**Validator:** _____________

---

## Pre-Deployment Validation

### Infrastructure Readiness

- [ ] Kubernetes cluster accessible via kubectl
- [ ] Namespace created successfully
- [ ] Secrets configured (DATABASE_URL, OPENAI_API_KEY, GITHUB_TOKEN)
- [ ] ConfigMap applied
- [ ] Database accessible from cluster
- [ ] pgvector extension installed in database
- [ ] Database migrations completed (alembic upgrade head)
- [ ] Docker images built and pushed to registry
- [ ] Ingress controller configured
- [ ] DNS records configured (if using custom domain)
- [ ] SSL/TLS certificates configured (if using HTTPS)

### Prerequisites Verified

- [ ] PostgreSQL 14+ with pgvector extension
- [ ] OpenAI API key valid and has credits
- [ ] GitHub token valid with required scopes (public_repo, read:org)
- [ ] Sufficient cluster resources (CPU, memory)
- [ ] Prometheus and Grafana accessible

---

## Deployment Validation

### API Service

- [ ] API deployment created successfully
- [ ] 2+ pods running and ready
- [ ] Service created and routing to pods
- [ ] Ingress created (if applicable)
- [ ] Health check endpoint responding: `/health`
- [ ] API v1 health endpoint responding: `/v1/health`
- [ ] Metrics endpoint responding: `/metrics`
- [ ] Liveness probe passing
- [ ] Readiness probe passing
- [ ] No CrashLoopBackOff errors
- [ ] No ImagePullBackOff errors
- [ ] Resource requests/limits appropriate

**API Pod Status:**
```bash
kubectl get pods -n <namespace> -l app=deeptech-api
```

**Expected Output:**
```
NAME                            READY   STATUS    RESTARTS   AGE
deeptech-api-xxxx-xxxx         1/1     Running   0          5m
deeptech-api-yyyy-yyyy         1/1     Running   0          5m
```

### Worker CronJobs

- [ ] arxiv-hourly CronJob created
- [ ] github-hourly CronJob created
- [ ] linking-daily CronJob created
- [ ] scoring-daily CronJob created
- [ ] opportunities-daily CronJob created
- [ ] All CronJobs have valid schedule syntax
- [ ] ConcurrencyPolicy set correctly (Forbid)
- [ ] Job history limits configured (3 successful, 3 failed)

**CronJob Status:**
```bash
kubectl get cronjobs -n <namespace>
```

**Expected Output:**
```
NAME                  SCHEDULE        SUSPEND   ACTIVE   LAST SCHEDULE   AGE
arxiv-hourly          0 * * * *       False     0        45m             1h
github-hourly         15 * * * *      False     0        30m             1h
linking-daily         30 2 * * *      False     0        <none>          1h
scoring-daily         0 3 * * *       False     0        <none>          1h
opportunities-daily   30 3 * * *      False     0        <none>          1h
```

---

## Functional Validation

### API Endpoints

Test all API endpoints with realistic queries:

#### 1. Health Endpoints

- [ ] `GET /health` returns 200 OK
  ```bash
  curl http://<api-url>/health
  ```
  Expected: `{"status": "healthy"}` or similar

- [ ] `GET /v1/health` returns 200 OK
  ```bash
  curl http://<api-url>/v1/health
  ```

#### 2. Papers Endpoints

- [ ] `GET /v1/papers` returns paper list
  ```bash
  curl "http://<api-url>/v1/papers?limit=10"
  ```
  Expected: JSON with `items` array, `total`, `limit`, `offset`

- [ ] `GET /v1/papers` with filters works
  ```bash
  curl "http://<api-url>/v1/papers?domain=AI&limit=5"
  ```
  Expected: Filtered results

- [ ] `GET /v1/papers` pagination works
  ```bash
  curl "http://<api-url>/v1/papers?limit=10&offset=10"
  ```
  Expected: Next page of results

- [ ] `GET /v1/papers/{id}` returns single paper (if implemented)

#### 3. Vector Search Endpoint

- [ ] `GET /v1/papers/near` with text_query works
  ```bash
  curl "http://<api-url>/v1/papers/near?text_query=quantum+computing&k=5"
  ```
  Expected: JSON with `items` array, similarity scores

- [ ] `GET /v1/papers/near` with paper_id works (if data exists)
  ```bash
  curl "http://<api-url>/v1/papers/near?paper_id=123&k=10"
  ```
  Expected: Similar papers to paper ID 123

- [ ] Vector search returns similarity scores
- [ ] Results ordered by similarity (highest first)

#### 4. Repositories Endpoint

- [ ] `GET /v1/repositories` returns repository list
  ```bash
  curl "http://<api-url>/v1/repositories?limit=10"
  ```
  Expected: JSON with `items` array

- [ ] `GET /v1/repositories` with filters works
  ```bash
  curl "http://<api-url>/v1/repositories?min_stars=100&limit=5"
  ```

#### 5. Opportunities Endpoint

- [ ] `GET /v1/opportunities` returns opportunities list
  ```bash
  curl "http://<api-url>/v1/opportunities?limit=10"
  ```
  Expected: JSON with `items` array, opportunities with composite scores

- [ ] `GET /v1/opportunities` filtering by domain works
  ```bash
  curl "http://<api-url>/v1/opportunities?domain=AI&limit=5"
  ```

- [ ] Opportunities have composite scores > 0.65
- [ ] Opportunities have recommendation tier (STRONG_BUY, BUY, WATCH, MONITOR)

#### 6. Metrics Endpoint

- [ ] `GET /metrics` returns Prometheus metrics
  ```bash
  curl http://<api-url>/metrics
  ```
  Expected: Prometheus format metrics

- [ ] Metrics include `api_requests_total`
- [ ] Metrics include `api_request_duration_seconds`
- [ ] Metrics include ingestion counters (if workers have run)

#### 7. Response Features

- [ ] All responses include proper Content-Type header (application/json)
- [ ] GZip compression enabled (check Content-Encoding header)
  ```bash
  curl -H "Accept-Encoding: gzip" -I "http://<api-url>/v1/papers?limit=10"
  ```
  Expected: `Content-Encoding: gzip`

- [ ] Error responses structured correctly (status, detail, timestamp)
  ```bash
  curl "http://<api-url>/v1/papers/999999999"
  ```
  Expected: 404 with structured error

---

## Data Pipeline Validation

### Manual Worker Job Execution

Trigger each worker manually to validate functionality:

#### 1. arXiv Ingestion

- [ ] Manually trigger arXiv job
  ```bash
  kubectl create job --from=cronjob/arxiv-hourly arxiv-manual-test -n <namespace>
  ```

- [ ] Job completes successfully (check status)
  ```bash
  kubectl get jobs -n <namespace>
  ```

- [ ] Check job logs for errors
  ```bash
  kubectl logs job/arxiv-manual-test -n <namespace>
  ```

- [ ] Verify papers ingested in database
  ```sql
  SELECT COUNT(*) FROM papers WHERE created_at > NOW() - INTERVAL '1 hour';
  ```

- [ ] Verify embeddings generated (embedding vector not null)

#### 2. GitHub Ingestion

- [ ] Manually trigger GitHub job
  ```bash
  kubectl create job --from=cronjob/github-hourly github-manual-test -n <namespace>
  ```

- [ ] Job completes successfully
- [ ] Check logs for rate limiting warnings
- [ ] Verify repositories ingested in database
  ```sql
  SELECT COUNT(*) FROM repositories WHERE created_at > NOW() - INTERVAL '1 hour';
  ```

#### 3. Linking Job

- [ ] Manually trigger linking job (after papers and repos exist)
  ```bash
  kubectl create job --from=cronjob/linking-daily linking-manual-test -n <namespace>
  ```

- [ ] Job completes successfully
- [ ] Verify links created in database
  ```sql
  SELECT COUNT(*) FROM paper_repo_links WHERE created_at > NOW() - INTERVAL '1 hour';
  ```

- [ ] Verify links have confidence scores
- [ ] Verify links have evidence field populated

#### 4. Scoring Job

- [ ] Manually trigger scoring job (after papers/repos/links exist)
  ```bash
  kubectl create job --from=cronjob/scoring-daily scoring-manual-test -n <namespace>
  ```

- [ ] Job completes successfully
- [ ] Verify all 6 scores calculated:
  ```sql
  SELECT 
    COUNT(*) as total_papers,
    COUNT(novelty_score) as has_novelty,
    COUNT(momentum_score) as has_momentum,
    COUNT(moat_score) as has_moat,
    COUNT(scalability_score) as has_scalability,
    COUNT(attention_gap_score) as has_attention_gap,
    COUNT(network_score) as has_network
  FROM papers;
  ```

- [ ] Verify composite scores calculated
- [ ] Verify score evidence populated

#### 5. Opportunities Generation

- [ ] Manually trigger opportunities job (after scoring)
  ```bash
  kubectl create job --from=cronjob/opportunities-daily opps-manual-test -n <namespace>
  ```

- [ ] Job completes successfully
- [ ] Verify opportunities created
  ```sql
  SELECT COUNT(*) FROM opportunities WHERE created_at > NOW() - INTERVAL '1 hour';
  ```

- [ ] Verify opportunities have composite_score > 0.65
- [ ] Verify opportunities have recommendation tier
- [ ] Verify opportunities have summary and thesis

---

## Performance Validation

### API Performance Baselines

- [ ] `/v1/papers` p95 latency < 300ms
  ```bash
  ab -n 100 -c 10 http://<api-url>/v1/papers?limit=10
  ```

- [ ] `/v1/papers/near` p95 latency < 500ms
  ```bash
  ab -n 50 -c 5 "http://<api-url>/v1/papers/near?text_query=quantum&k=10"
  ```

- [ ] No memory leaks over 1 hour of operation
  ```bash
  kubectl top pods -n <namespace> -l app=deeptech-api
  ```

- [ ] CPU usage stable under load
- [ ] Pod restarts = 0 (check `kubectl get pods`)

### Database Performance

- [ ] Vector search queries complete < 500ms
- [ ] EXPLAIN plans show index usage
- [ ] No slow query warnings in logs
- [ ] Connection pool not exhausted

---

## Monitoring & Observability

### Prometheus Metrics

- [ ] Prometheus scraping API pods successfully
- [ ] Metrics endpoint accessible from Prometheus
- [ ] Key metrics visible:
  - [ ] `api_requests_total`
  - [ ] `api_request_duration_seconds`
  - [ ] `ingest_arxiv_papers_processed_total`
  - [ ] `ingest_github_repos_processed_total`

### Grafana Dashboards

- [ ] Grafana connected to Prometheus
- [ ] Overview dashboard showing data
- [ ] API Performance dashboard showing data
- [ ] No "No Data" panels (after worker jobs run)

### Alerting

- [ ] Alert rules loaded in Prometheus
- [ ] Test alerts can fire (optional: trigger a test alert)
- [ ] Alert manager configured (if using)
- [ ] Alert notification channels configured

---

## Data Quality Validation

### Papers

- [ ] Papers have valid arXiv IDs
- [ ] Papers have titles and abstracts
- [ ] Papers have embeddings (vector not null)
- [ ] Papers have published_at dates
- [ ] Papers have domain classification
- [ ] Papers have authors

### Repositories

- [ ] Repositories have valid GitHub URLs
- [ ] Repositories have README content
- [ ] Repositories have star counts
- [ ] Repositories have created_at dates
- [ ] Repositories have velocity scores (after scoring)

### Links

- [ ] Links have confidence scores (0.0 to 1.0)
- [ ] Links have evidence field populated
- [ ] Link confidence distribution reasonable (>60% have conf > 0.6)

### Scores

- [ ] All 6 scores normalized (0.0 to 1.0)
- [ ] Composite scores calculated correctly
- [ ] Score evidence includes all 6 dimensions
- [ ] Z-score normalization applied at domain level

### Opportunities

- [ ] Only opportunities with composite_score > 0.65
- [ ] Recommendation tiers distributed appropriately
- [ ] Summaries generated
- [ ] Investment thesis populated
- [ ] Weekly freeze logic working (no duplicates within 4 weeks)

---

## Security Validation

- [ ] Secrets not exposed in logs
- [ ] API does not expose internal error details
- [ ] Database credentials encrypted in cluster
- [ ] No hardcoded credentials in code
- [ ] HTTPS enabled (if public-facing)
- [ ] Network policies configured (if required)

---

## Operational Readiness

### Documentation

- [ ] Deployment guide complete
- [ ] Runbooks created for common scenarios
- [ ] API documentation available
- [ ] Architecture diagrams up to date

### Backup & Recovery

- [ ] Database backup automation configured
- [ ] Backup restore tested in staging
- [ ] Recovery Time Objective (RTO) documented
- [ ] Recovery Point Objective (RPO) documented

### Runbooks Available

- [ ] Worker failure runbook
- [ ] Database rollback runbook
- [ ] API incident response runbook
- [ ] GitHub rate limit runbook
- [ ] Alert response runbook

---

## Go/No-Go Decision

### Staging Sign-Off

- [ ] All critical checks passed
- [ ] No P0/P1 bugs found
- [ ] Performance baselines met
- [ ] Stable for 48+ hours
- [ ] Team trained on operations

**Staging Approved:** ☐ Yes  ☐ No  
**Approver:** _____________  
**Date:** _____________

### Production Sign-Off

- [ ] Staging stable for 7+ days
- [ ] All validation checks passed
- [ ] Backup/restore tested
- [ ] Monitoring confirmed working
- [ ] Runbooks reviewed
- [ ] Team ready for production support

**Production Approved:** ☐ Yes  ☐ No  
**Approver:** _____________  
**Date:** _____________

---

## Notes

Use this section to document any issues, deviations, or observations:

```
_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```

---

**Validation Completed By:** _____________  
**Date:** _____________  
**Environment:** ☐ Staging  ☐ Production
