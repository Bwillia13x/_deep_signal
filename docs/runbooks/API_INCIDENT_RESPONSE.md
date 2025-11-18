# Runbook: API Incident Response

**Severity:** P1 (Critical)  
**Service:** DeepTech Radar API  
**Last Updated:** November 18, 2025

---

## Overview

This runbook provides step-by-step procedures for responding to API service incidents, including outages, high error rates, performance degradation, and other critical issues.

---

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **P0** | Complete outage | Immediate | API completely down, all requests failing |
| **P1** | Severe degradation | <15 min | >50% error rate, p95 latency >5s |
| **P2** | Partial degradation | <1 hour | 10-50% error rate, elevated latency |
| **P3** | Minor issues | <4 hours | Single endpoint issues, <10% error rate |

---

## Initial Response

### Step 1: Assess Severity

Quick checks to determine severity:

```bash
# Check pod status
kubectl get pods -n <namespace> -l app=deeptech-api

# Check recent pod restarts
kubectl get pods -n <namespace> -l app=deeptech-api -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'

# Check service endpoints
kubectl get endpoints -n <namespace> deeptech-api

# Quick health check
kubectl port-forward -n <namespace> svc/deeptech-api 8000:8000 &
curl http://localhost:8000/health
```

### Step 2: Check Monitoring

Review Grafana dashboards:
- **Overview Dashboard**: Overall system health
- **API Performance Dashboard**: Request rates, latencies, errors

Check Prometheus alerts:
- `HighErrorRate`: >5% error rate
- `SlowAPIRequests`: p95 > 500ms
- `APIDown`: Health check failing

### Step 3: Communicate

```
INCIDENT TEMPLATE:
------------------
Status: INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
Severity: P0 / P1 / P2 / P3
Service: DeepTech Radar API
Impact: [Brief description of user impact]
Start Time: [Timestamp]
Updates: [Link to status page or communication channel]
```

Post initial communication within:
- P0: 5 minutes
- P1: 15 minutes
- P2: 30 minutes

---

## Common Incident Scenarios

### Scenario 1: Complete API Outage (P0)

**Symptoms:**
- All API requests return 502/503/504
- Health checks failing
- No pods running or all pods in CrashLoopBackOff
- Ingress showing no healthy backends

**Diagnosis:**

```bash
# Check pod status
kubectl get pods -n <namespace> -l app=deeptech-api

# Check pod events
kubectl describe pods -n <namespace> -l app=deeptech-api

# Check recent logs
kubectl logs -n <namespace> -l app=deeptech-api --tail=100
```

**Common Causes & Resolutions:**

#### 1. Database Connection Failure

**Symptoms in logs:**
```
sqlalchemy.exc.OperationalError: could not connect to server
FATAL: no pg_hba.conf entry for host
```

**Resolution:**
```bash
# Verify DATABASE_URL secret
kubectl get secret deeptech-secrets -n <namespace> -o jsonpath='{.data.database-url}' | base64 -d

# Test database from debug pod
kubectl run -it --rm db-test --image=postgres:14 --restart=Never -n <namespace> -- \
  psql "${DATABASE_URL}" -c "SELECT 1;"

# If database is down, check database server status
# If connection string is wrong, update secret
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${CORRECT_DATABASE_URL}" \
  --namespace=<namespace> \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployment
kubectl rollout restart deployment/deeptech-api -n <namespace>
```

#### 2. Image Pull Failure

**Symptoms in events:**
```
Failed to pull image: unauthorized
ErrImagePull
ImagePullBackOff
```

**Resolution:**
```bash
# Check image exists and tag is correct
kubectl describe pod <pod-name> -n <namespace> | grep Image

# Verify image pull secret (if using private registry)
kubectl get secret -n <namespace>

# Update deployment with correct image
kubectl set image deployment/deeptech-api \
  api=ghcr.io/yourorg/deeptech-radar-api:latest \
  -n <namespace>
```

#### 3. Out of Memory / Resource Constraints

**Symptoms in events:**
```
OOMKilled
Pod evicted due to resource constraints
```

**Resolution:**
```bash
# Check resource usage
kubectl top pods -n <namespace> -l app=deeptech-api

# Increase memory limits
kubectl edit deployment deeptech-api -n <namespace>
# Update: resources.limits.memory to "1Gi" or higher

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Scenario 2: High Error Rate (P1)

**Symptoms:**
- 20-50% of requests returning 500 errors
- Prometheus alert: `HighErrorRate`
- Some requests succeed, others fail intermittently

**Diagnosis:**

```bash
# Check error logs
kubectl logs -n <namespace> -l app=deeptech-api --tail=500 | grep -i error

# Check metrics
curl http://localhost:8000/metrics | grep api_requests_total

# Identify failing endpoints
kubectl logs -n <namespace> -l app=deeptech-api --tail=1000 | grep "500"
```

**Common Causes & Resolutions:**

#### 1. Database Query Timeouts

**Symptoms in logs:**
```
sqlalchemy.exc.TimeoutError
Query exceeded timeout
```

**Resolution:**
```bash
# Check for long-running queries in database
kubectl run -it --rm psql --image=postgres:14 --restart=Never -n <namespace> -- \
  psql "${DATABASE_URL}" -c "
    SELECT pid, now() - query_start as duration, query
    FROM pg_stat_activity
    WHERE state = 'active' AND now() - query_start > interval '5 seconds'
    ORDER BY duration DESC;
  "

# Kill long-running queries if necessary
# psql> SELECT pg_terminate_backend(pid);

# Add missing indexes (if identified)
# Review query plans with EXPLAIN ANALYZE

# Increase timeout temporarily
kubectl edit deployment deeptech-api -n <namespace>
# Add env var: DATABASE_QUERY_TIMEOUT: "60"
```

#### 2. External Service Failures (OpenAI, GitHub)

**Symptoms in logs:**
```
OpenAI API error: 500 Internal Server Error
GitHub API: 503 Service Unavailable
```

**Resolution:**
```bash
# Check external service status
curl -I https://api.openai.com/
curl -I https://api.github.com/

# Implement circuit breaker / graceful degradation
# For now, disable affected features temporarily
# Or increase retry limits / timeouts
```

### Scenario 3: Slow Response Times (P1/P2)

**Symptoms:**
- p95 latency >1s (normal <300ms)
- Prometheus alert: `SlowAPIRequests`
- Requests eventually succeed but take too long

**Diagnosis:**

```bash
# Check current latency
ab -n 100 -c 10 http://localhost:8000/v1/papers?limit=10

# Check pod resource usage
kubectl top pods -n <namespace> -l app=deeptech-api

# Check database connection pool
kubectl logs -n <namespace> -l app=deeptech-api | grep "connection pool"
```

**Common Causes & Resolutions:**

#### 1. Database Slow Queries

**Resolution:**
```bash
# Identify slow queries
kubectl run -it --rm psql --image=postgres:14 --restart=Never -n <namespace> -- \
  psql "${DATABASE_URL}" -c "
    SELECT query, mean_exec_time, calls
    FROM pg_stat_statements
    ORDER BY mean_exec_time DESC
    LIMIT 10;
  "

# Check for missing indexes
# Review EXPLAIN plans
# Add indexes where needed
```

#### 2. Connection Pool Exhaustion

**Symptoms in logs:**
```
QueuePool limit of size 10 overflow 20 reached
Timeout waiting for connection from pool
```

**Resolution:**
```bash
# Increase pool size
kubectl edit deployment deeptech-api -n <namespace>
# Add env vars:
# DB_POOL_SIZE: "20"
# DB_MAX_OVERFLOW: "40"

# Or scale up replicas to distribute load
kubectl scale deployment/deeptech-api -n <namespace> --replicas=4
```

#### 3. Insufficient CPU

**Resolution:**
```bash
# Check CPU throttling
kubectl top pods -n <namespace> -l app=deeptech-api

# Increase CPU limits
kubectl edit deployment deeptech-api -n <namespace>
# Update: resources.limits.cpu to "1000m" or higher

# Scale horizontally
kubectl scale deployment/deeptech-api -n <namespace> --replicas=4
```

### Scenario 4: Specific Endpoint Failure (P2)

**Symptoms:**
- One endpoint consistently failing
- Other endpoints working fine
- Targeted errors in logs

**Diagnosis:**

```bash
# Test specific endpoint
curl -v http://localhost:8000/v1/papers/near?text_query=quantum&k=5

# Check logs for that endpoint
kubectl logs -n <namespace> -l app=deeptech-api | grep "/v1/papers/near"
```

**Resolution:**
- Identify root cause from logs
- May be specific to that endpoint's logic
- Consider disabling endpoint temporarily if critical
- Deploy hotfix if code bug identified

---

## Emergency Procedures

### Complete Service Restart

If nothing else works:

```bash
# Scale to 0 and back up (forces complete restart)
kubectl scale deployment/deeptech-api -n <namespace> --replicas=0
sleep 10
kubectl scale deployment/deeptech-api -n <namespace> --replicas=2

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=deeptech-api -n <namespace> --timeout=180s

# Verify health
curl http://localhost:8000/health
```

### Rollback to Previous Version

If issues started after recent deployment:

```bash
# Rollback deployment
kubectl rollout undo deployment/deeptech-api -n <namespace>

# Check rollback status
kubectl rollout status deployment/deeptech-api -n <namespace>

# Verify rollback
kubectl describe deployment deeptech-api -n <namespace> | grep Image
```

### Enable Maintenance Mode

If you need time to fix issues:

```bash
# Create a maintenance page ConfigMap
kubectl create configmap maintenance-page -n <namespace> \
  --from-literal=html='<html><body><h1>Maintenance in Progress</h1><p>We will be back soon.</p></body></html>'

# Update ingress to serve maintenance page
# (This depends on your ingress controller configuration)
# Typically involves adding an annotation or custom backend
```

---

## Monitoring During Incident

**Key Metrics to Watch:**

1. **Error Rate**
   ```
   rate(api_requests_total{status=~"5.."}[5m]) / rate(api_requests_total[5m])
   ```

2. **Latency**
   ```
   histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
   ```

3. **Request Rate**
   ```
   rate(api_requests_total[5m])
   ```

4. **Pod Restarts**
   ```bash
   kubectl get pods -n <namespace> -l app=deeptech-api --watch
   ```

---

## Post-Incident

### Step 1: Verify Resolution

- [ ] Error rate back to normal (<1%)
- [ ] Latency back to baseline (p95 <300ms)
- [ ] All pods healthy and stable
- [ ] No restarts for 30+ minutes
- [ ] Monitoring shows normal patterns

### Step 2: Communication

Update stakeholders:
```
INCIDENT RESOLVED
-----------------
Status: RESOLVED
Severity: [P0/P1/P2]
Duration: [X hours Y minutes]
Root Cause: [Brief description]
Resolution: [What was done]
Prevention: [What will be done to prevent recurrence]
```

### Step 3: Post-Mortem (for P0/P1 incidents)

Within 48 hours, create post-mortem document:

- **Timeline**: Detailed timeline of events
- **Root Cause**: Technical root cause analysis
- **Impact**: User impact assessment
- **Resolution**: How issue was resolved
- **Action Items**: Prevent recurrence
  - Code changes needed
  - Monitoring improvements
  - Documentation updates
  - Training needs

---

## Prevention

### Proactive Measures

1. **Enable health checks** on all critical dependencies
2. **Set up comprehensive alerts** for all key metrics
3. **Regular load testing** to identify bottlenecks
4. **Database query optimization** and index maintenance
5. **Implement circuit breakers** for external services
6. **Graceful degradation** when services unavailable
7. **Regular chaos engineering** exercises
8. **Keep runbooks up-to-date**

### Pre-Deployment Checklist

Before each production deployment:

- [ ] Changes tested in staging
- [ ] Performance testing completed
- [ ] Database migrations tested
- [ ] Rollback plan ready
- [ ] Monitoring confirmed working
- [ ] Team notified of deployment
- [ ] Incident response team on standby

---

## Escalation

**When to escalate:**
- P0 incident not resolved within 1 hour
- P1 incident not resolved within 4 hours
- Multiple simultaneous incidents
- Data loss or corruption
- Security breach suspected

**Escalation Path:**
1. On-call backend engineer
2. Senior backend engineer
3. Engineering manager
4. CTO

---

## Related Runbooks

- [Worker Failure](./WORKER_FAILURE.md)
- [Database Rollback](./DATABASE_ROLLBACK.md)
- [GitHub Rate Limit](./GITHUB_RATE_LIMIT.md)
- [Alert Response](./ALERT_RESPONSE.md)

---

**Last Reviewed:** November 18, 2025
