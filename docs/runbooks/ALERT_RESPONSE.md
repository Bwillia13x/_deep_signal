# Runbook: Alert Response Guide

**Service:** DeepTech Radar Monitoring  
**Last Updated:** November 18, 2025

---

## Overview

This runbook provides quick reference for responding to Prometheus alerts in the DeepTech Radar system. Each alert includes diagnosis steps and resolution procedures.

---

## Alert Severity Levels

| Level | Response Time | Description |
|-------|---------------|-------------|
| **Critical** | Immediate (<5 min) | Service down or severe degradation |
| **Warning** | <30 min | Potential issues, degraded performance |
| **Info** | <4 hours | Informational, may need investigation |

---

## API Alerts

### HighErrorRate

**Severity:** Critical  
**Threshold:** >5% error rate for 5 minutes  
**Impact:** Users experiencing failed requests

#### Diagnosis

```bash
# Check error rate
kubectl logs -n <namespace> -l app=deeptech-api --tail=200 | grep -c "500"

# Check which endpoints failing
kubectl logs -n <namespace> -l app=deeptech-api --tail=500 | grep "500" | awk '{print $6}' | sort | uniq -c

# Check error types
kubectl logs -n <namespace> -l app=deeptech-api --tail=500 | grep -i error
```

#### Resolution

**Common causes:**
1. Database connection issues → See [API Incident Response](./API_INCIDENT_RESPONSE.md#scenario-1-database-connection-failure)
2. External API failures → Check OpenAI/GitHub status
3. Code bug → Review recent deployments, consider rollback

**Quick fixes:**
```bash
# Restart pods
kubectl rollout restart deployment/deeptech-api -n <namespace>

# If persists, rollback
kubectl rollout undo deployment/deeptech-api -n <namespace>
```

---

### SlowAPIRequests

**Severity:** Warning  
**Threshold:** p95 latency >500ms for 10 minutes  
**Impact:** Degraded user experience

#### Diagnosis

```bash
# Check current latency
ab -n 100 -c 10 http://localhost:8000/v1/papers?limit=10

# Check pod resource usage
kubectl top pods -n <namespace> -l app=deeptech-api

# Check slow queries in database
kubectl run -it --rm psql --image=postgres:14 --restart=Never -n <namespace> -- \
  psql "${DATABASE_URL}" -c "
    SELECT query, mean_exec_time, calls
    FROM pg_stat_statements
    ORDER BY mean_exec_time DESC
    LIMIT 5;
  "
```

#### Resolution

**Common causes:**
1. Slow database queries → Add indexes, optimize queries
2. CPU/memory constraints → Increase resources or scale up
3. Connection pool exhaustion → Increase pool size

**Quick fixes:**
```bash
# Scale up replicas
kubectl scale deployment/deeptech-api -n <namespace> --replicas=4

# Increase resources
kubectl edit deployment deeptech-api -n <namespace>
# Update resources.limits.cpu and memory
```

---

### APIDown

**Severity:** Critical  
**Threshold:** Health check failing for 2 minutes  
**Impact:** Complete service outage

#### Diagnosis

```bash
# Check pod status
kubectl get pods -n <namespace> -l app=deeptech-api

# Check pod logs
kubectl logs -n <namespace> -l app=deeptech-api --tail=100

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep api
```

#### Resolution

Follow [API Incident Response](./API_INCIDENT_RESPONSE.md#scenario-1-complete-api-outage-p0)

**Immediate actions:**
```bash
# Check if pods are running
kubectl get pods -n <namespace> -l app=deeptech-api

# If not running, check deployment
kubectl describe deployment deeptech-api -n <namespace>

# Force recreate pods
kubectl rollout restart deployment/deeptech-api -n <namespace>
```

---

## Ingestion Alerts

### ArxivIngestionStalled

**Severity:** Warning  
**Threshold:** No papers ingested in 2 hours  
**Impact:** Data pipeline blocked, outdated data

#### Diagnosis

```bash
# Check last successful arXiv job
kubectl get jobs -n <namespace> -l app=arxiv-worker --sort-by='.status.completionTime'

# Check recent job logs
kubectl logs -n <namespace> job/<latest-job-name>

# Check CronJob status
kubectl get cronjob arxiv-hourly -n <namespace>
```

#### Resolution

**Common causes:**
1. CronJob suspended → Resume CronJob
2. Job failing → Check logs, see [Worker Failure](./WORKER_FAILURE.md)
3. OpenAI API issues → Check API key and quota

**Quick fixes:**
```bash
# Check if suspended
kubectl get cronjob arxiv-hourly -n <namespace>

# Resume if suspended
kubectl patch cronjob arxiv-hourly -n <namespace> -p '{"spec":{"suspend":false}}'

# Manually trigger job
kubectl create job --from=cronjob/arxiv-hourly arxiv-manual-$(date +%s) -n <namespace>
```

---

### GitHubIngestionStalled

**Severity:** Warning  
**Threshold:** No repos ingested in 3 hours  
**Impact:** Repository data outdated

#### Diagnosis

```bash
# Check last successful GitHub job
kubectl get jobs -n <namespace> -l app=github-worker --sort-by='.status.completionTime'

# Check rate limit status
curl -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/rate_limit | jq '.resources.core'

# Check job logs
kubectl logs -n <namespace> job/<latest-job-name>
```

#### Resolution

**Common causes:**
1. GitHub rate limit → See [GitHub Rate Limit](./GITHUB_RATE_LIMIT.md)
2. Invalid token → Update secret
3. Job failing → Check logs

**Quick fixes:**
```bash
# If rate limited, wait for reset or reduce frequency
kubectl edit cronjob github-hourly -n <namespace>
# Change to: schedule: "15 */2 * * *"  # Every 2 hours

# Manually trigger when quota available
kubectl create job --from=cronjob/github-hourly github-manual-$(date +%s) -n <namespace>
```

---

## Database Alerts

### DatabaseConnectionFailures

**Severity:** Critical  
**Threshold:** Connection failures detected  
**Impact:** API and workers cannot access data

#### Diagnosis

```bash
# Check database connectivity
kubectl run -it --rm db-test --image=postgres:14 --restart=Never -n <namespace> -- \
  psql "${DATABASE_URL}" -c "SELECT 1;"

# Check database server (if managed externally)
# - Cloud provider console
# - SSH to database server

# Check connection pool
kubectl logs -n <namespace> -l app=deeptech-api | grep -i "connection"
```

#### Resolution

**Common causes:**
1. Database server down → Restart database server
2. Wrong credentials → Update DATABASE_URL secret
3. Network issues → Check network policies, firewall
4. Connection pool exhausted → Increase pool size or restart API

**Quick fixes:**
```bash
# Restart API pods (resets connection pool)
kubectl rollout restart deployment/deeptech-api -n <namespace>

# Update DATABASE_URL if wrong
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${CORRECT_DATABASE_URL}" \
  --namespace=<namespace> \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

### HighDatabaseConnectionTime

**Severity:** Warning  
**Threshold:** Connection time >100ms  
**Impact:** Slow API responses

#### Diagnosis

```bash
# Check database server load
# Connect to database server or check cloud metrics

# Check connection pool settings
kubectl describe deployment deeptech-api -n <namespace> | grep -i env

# Check network latency
kubectl run -it --rm network-test --image=alpine --restart=Never -n <namespace> -- \
  ping <database-host>
```

#### Resolution

**Common causes:**
1. Network latency → Move database closer to cluster
2. Database overloaded → Scale database resources
3. Connection pool too small → Increase pool size

---

## Worker Job Alerts

### WorkerJobFailures

**Severity:** Warning  
**Threshold:** Job failed in last hour  
**Impact:** Data pipeline incomplete

#### Diagnosis

```bash
# List recent failed jobs
kubectl get jobs -n <namespace> --field-selector status.successful=0

# Check specific job logs
kubectl logs -n <namespace> job/<failed-job-name>

# Check CronJob configuration
kubectl describe cronjob <cronjob-name> -n <namespace>
```

#### Resolution

Follow [Worker Failure](./WORKER_FAILURE.md) runbook.

**Quick check:**
```bash
# Retry failed job manually
kubectl create job --from=cronjob/<cronjob-name> retry-$(date +%s) -n <namespace>

# Watch job
kubectl get jobs -n <namespace> -w
```

---

## System Alerts

### HighMemoryUsage

**Severity:** Warning  
**Threshold:** Pod memory >80% of limit  
**Impact:** Risk of OOM kills

#### Diagnosis

```bash
# Check current memory usage
kubectl top pods -n <namespace> -l app=deeptech-api

# Check memory limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Limits"

# Check for memory leaks
kubectl logs -n <namespace> <pod-name> --tail=500 | grep -i memory
```

#### Resolution

**Quick fixes:**
```bash
# Increase memory limits
kubectl edit deployment deeptech-api -n <namespace>
# Update: resources.limits.memory: "2Gi"

# Or scale horizontally
kubectl scale deployment/deeptech-api -n <namespace> --replicas=4

# Restart pods to clear memory
kubectl rollout restart deployment/deeptech-api -n <namespace>
```

---

### HighCPUUsage

**Severity:** Warning  
**Threshold:** Pod CPU >80% of limit  
**Impact:** Slow response times, request queuing

#### Diagnosis

```bash
# Check current CPU usage
kubectl top pods -n <namespace> -l app=deeptech-api

# Check CPU limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Limits"

# Profile CPU usage (if tools available)
kubectl exec -it <pod-name> -n <namespace> -- top
```

#### Resolution

**Quick fixes:**
```bash
# Increase CPU limits
kubectl edit deployment deeptech-api -n <namespace>
# Update: resources.limits.cpu: "1000m"

# Scale horizontally (preferred)
kubectl scale deployment/deeptech-api -n <namespace> --replicas=4
```

---

## Alert Workflow

### Step 1: Acknowledge Alert

- Note alert time and details
- Communicate to team if severity is Critical

### Step 2: Quick Assessment

```bash
# Overall system health
kubectl get pods -n <namespace>
kubectl get nodes
kubectl top nodes
kubectl top pods -n <namespace>
```

### Step 3: Follow Specific Runbook

- Use guidance above for specific alert
- Refer to linked detailed runbooks
- Document actions taken

### Step 4: Resolve or Escalate

**If resolved:**
- Verify metrics return to normal
- Document root cause
- Close alert

**If not resolved in expected time:**
- Escalate per severity level
- Engage next tier of support

### Step 5: Post-Incident

For Critical alerts:
- Create incident report
- Schedule post-mortem (within 48h)
- Identify prevention measures

---

## Alert Contact Matrix

| Alert Type | Primary Contact | Escalation |
|------------|----------------|------------|
| API Down | On-call engineer | Senior backend engineer |
| Database Issues | Database admin | Platform team |
| Worker Failures | Data engineer | Backend team |
| Infrastructure | DevOps engineer | Infrastructure team |

---

## Useful Commands Cheatsheet

```bash
# Pod status
kubectl get pods -n <namespace> -l app=deeptech-api

# Pod logs
kubectl logs -n <namespace> -l app=deeptech-api --tail=100 -f

# Resource usage
kubectl top pods -n <namespace>

# Restart deployment
kubectl rollout restart deployment/deeptech-api -n <namespace>

# Scale deployment
kubectl scale deployment/deeptech-api -n <namespace> --replicas=3

# Port forward for testing
kubectl port-forward -n <namespace> svc/deeptech-api 8000:8000

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- bash

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

---

## Related Documentation

- [API Incident Response](./API_INCIDENT_RESPONSE.md)
- [Worker Failure](./WORKER_FAILURE.md)
- [Database Rollback](./DATABASE_ROLLBACK.md)
- [GitHub Rate Limit](./GITHUB_RATE_LIMIT.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)

---

**Last Reviewed:** November 18, 2025
