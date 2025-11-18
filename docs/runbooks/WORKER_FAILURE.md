# Runbook: Worker Job Failure

**Severity:** P2 (High)  
**Service:** Worker CronJobs  
**Last Updated:** November 18, 2025

---

## Overview

This runbook covers troubleshooting and recovery procedures for failed worker CronJobs in the DeepTech Radar system. Worker jobs include:
- **arxiv-hourly**: Paper ingestion from arXiv
- **github-hourly**: Repository ingestion from GitHub
- **linking-daily**: Link papers to repositories
- **scoring-daily**: Calculate 6D scores
- **opportunities-daily**: Generate investment opportunities

---

## Symptoms

- CronJob shows failed job(s) in history
- Metrics show no recent ingestion activity
- Prometheus alerts: `ArxivIngestionStalled`, `WorkerJobFailures`
- Job pods in Error or Failed state
- Gaps in data ingestion timeline

---

## Initial Diagnosis

### Step 1: Check CronJob Status

```bash
# List all CronJobs
kubectl get cronjobs -n <namespace>

# Check specific CronJob
kubectl describe cronjob <cronjob-name> -n <namespace>
```

**Look for:**
- Last successful schedule time
- Active jobs count
- Failed jobs in history

### Step 2: Check Recent Jobs

```bash
# List jobs from CronJob
kubectl get jobs -n <namespace> -l app=<worker-name>

# Example for arxiv worker:
kubectl get jobs -n <namespace> -l app=arxiv-worker
```

**Job States:**
- `Complete`: Job succeeded
- `Failed`: Job failed (check why)
- `Running`: Job in progress

### Step 3: Check Pod Logs

```bash
# Get pod name from failed job
kubectl get pods -n <namespace> -l job-name=<job-name>

# View logs
kubectl logs <pod-name> -n <namespace>

# For completed jobs (pod may be terminated)
kubectl logs job/<job-name> -n <namespace>
```

**Common log patterns:**
- Database connection errors
- API rate limiting (GitHub, OpenAI)
- Out of memory errors
- Timeout errors
- Missing environment variables

---

## Common Failure Scenarios

### Scenario 1: Database Connection Failure

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
FATAL: remaining connection slots are reserved
```

**Causes:**
- Wrong DATABASE_URL in secrets
- Database server unreachable
- Connection pool exhausted
- Network policy blocking access

**Resolution:**

1. Verify DATABASE_URL secret:
   ```bash
   kubectl get secret deeptech-secrets -n <namespace> -o jsonpath='{.data.database-url}' | base64 -d
   ```

2. Test database connectivity from pod:
   ```bash
   kubectl run -it --rm debug --image=postgres:14 --restart=Never -n <namespace> -- \
     psql "${DATABASE_URL}"
   ```

3. Check database server status:
   ```bash
   # SSH to database server or check cloud provider console
   systemctl status postgresql
   ```

4. Check connection pool settings in application
5. Restart API pods if connection pool exhausted:
   ```bash
   kubectl rollout restart deployment/deeptech-api -n <namespace>
   ```

### Scenario 2: GitHub Rate Limiting

**Symptoms:**
```
GitHub API rate limit exceeded
403 Forbidden: rate limit exceeded
```

**Causes:**
- Token quota exhausted (5000 req/hour for authenticated)
- Multiple workers using same token
- Token not configured correctly

**Resolution:**

1. Check rate limit status:
   ```bash
   curl -H "Authorization: token ${GITHUB_TOKEN}" https://api.github.com/rate_limit
   ```

2. Wait for rate limit reset (shown in API response)

3. Reduce ingestion frequency:
   ```bash
   # Edit CronJob schedule from hourly to every 2 hours
   kubectl edit cronjob github-hourly -n <namespace>
   # Change schedule: "0 */2 * * *"
   ```

4. Use multiple GitHub tokens (if available):
   - Add token rotation logic to worker
   - Update secrets with additional tokens

5. Reduce `GITHUB_MAX_REPOS` in ConfigMap:
   ```bash
   kubectl edit configmap deeptech-config -n <namespace>
   # Set GITHUB_MAX_REPOS: "250"
   ```

See also: [GitHub Rate Limit Runbook](./GITHUB_RATE_LIMIT.md)

### Scenario 3: OpenAI API Errors

**Symptoms:**
```
openai.error.RateLimitError: Rate limit exceeded
openai.error.APIError: The server had an error processing your request
openai.error.InvalidRequestError: Invalid request
```

**Causes:**
- API quota exhausted
- Invalid API key
- Request too large
- Service outage

**Resolution:**

1. Verify API key:
   ```bash
   kubectl get secret deeptech-secrets -n <namespace> -o jsonpath='{.data.openai-api-key}' | base64 -d
   ```

2. Check OpenAI service status:
   - Visit: https://status.openai.com/

3. Check quota/billing:
   - Login to OpenAI dashboard
   - Verify usage limits and billing

4. Reduce batch size temporarily:
   ```bash
   kubectl edit configmap deeptech-config -n <namespace>
   # Reduce ARXIV_MAX_RESULTS, SCORING_BATCH_SIZE
   ```

5. Implement exponential backoff in code (if not present)

6. Switch to alternative embedding provider (if configured)

### Scenario 4: Out of Memory (OOM)

**Symptoms:**
```
OOMKilled
Exit code 137
```

**Causes:**
- Batch size too large
- Memory leak
- Insufficient memory limits

**Resolution:**

1. Check pod memory usage before failure:
   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   ```
   Look for: `Last State: Terminated, Reason: OOMKilled`

2. Reduce batch sizes:
   ```bash
   kubectl edit configmap deeptech-config -n <namespace>
   # Reduce: LINKING_BATCH_SIZE, SCORING_BATCH_SIZE
   ```

3. Increase memory limits:
   ```bash
   kubectl edit cronjob <cronjob-name> -n <namespace>
   # Update resources.limits.memory to "2Gi" or higher
   ```

4. Check for memory leaks in application code
5. Profile worker job memory usage locally

### Scenario 5: Job Timeout / Backoff Limit Exceeded

**Symptoms:**
```
Job has reached the specified backoff limit
DeadlineExceeded
```

**Causes:**
- Job takes longer than allowed
- Job keeps failing and retrying
- BackoffLimit reached (default: 6)

**Resolution:**

1. Check job definition:
   ```bash
   kubectl get job <job-name> -n <namespace> -o yaml
   ```
   Look for: `backoffLimit`, `activeDeadlineSeconds`

2. Increase backoff limit in CronJob:
   ```bash
   kubectl edit cronjob <cronjob-name> -n <namespace>
   # spec.jobTemplate.spec.backoffLimit: 3
   ```

3. Increase deadline if job legitimately takes long:
   ```bash
   kubectl edit cronjob <cronjob-name> -n <namespace>
   # spec.jobTemplate.spec.activeDeadlineSeconds: 7200  # 2 hours
   ```

4. Optimize job performance:
   - Add database indexes
   - Reduce batch size
   - Parallelize where possible

---

## Recovery Procedures

### Procedure 1: Manual Job Re-run

If a scheduled job failed, run it manually:

```bash
# Create one-time job from CronJob
kubectl create job --from=cronjob/<cronjob-name> <job-name>-manual -n <namespace>

# Example:
kubectl create job --from=cronjob/arxiv-hourly arxiv-retry-$(date +%s) -n <namespace>

# Watch job progress
kubectl get jobs -n <namespace> -w

# Check logs
kubectl logs job/<job-name>-manual -n <namespace> -f
```

### Procedure 2: Update Secrets

If secret values are wrong:

```bash
# Update secret
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=openai-api-key="${OPENAI_API_KEY}" \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --namespace=<namespace> \
  --dry-run=client -o yaml | kubectl apply -f -

# Secrets are mounted as volumes, so pods should get new values
# If not, restart the deployment:
kubectl rollout restart deployment/deeptech-api -n <namespace>
```

### Procedure 3: Adjust Job Schedule

To prevent overlapping jobs or reduce frequency:

```bash
# Edit CronJob schedule
kubectl edit cronjob <cronjob-name> -n <namespace>

# Common schedules:
# Every hour:        0 * * * *
# Every 2 hours:     0 */2 * * *
# Every 4 hours:     0 */4 * * *
# Twice daily:       0 6,18 * * *
# Daily at 3am:      0 3 * * *
```

### Procedure 4: Suspend CronJob

If job is consistently failing and needs investigation:

```bash
# Suspend CronJob
kubectl patch cronjob <cronjob-name> -n <namespace> -p '{"spec":{"suspend":true}}'

# Verify suspension
kubectl get cronjob <cronjob-name> -n <namespace>

# Resume when fixed
kubectl patch cronjob <cronjob-name> -n <namespace> -p '{"spec":{"suspend":false}}'
```

### Procedure 5: Clean Up Failed Jobs

Failed jobs accumulate, clean them up:

```bash
# Delete specific job
kubectl delete job <job-name> -n <namespace>

# Delete all failed jobs for a CronJob
kubectl delete job -n <namespace> -l app=<worker-name> --field-selector status.successful=0

# CronJob automatically limits history (successfulJobsHistoryLimit, failedJobsHistoryLimit)
```

---

## Prevention

### Best Practices

1. **Set appropriate resource limits** based on workload
2. **Configure backoff limits** to prevent infinite retries
3. **Implement retries with exponential backoff** in code
4. **Monitor job success rate** with Prometheus alerts
5. **Use ConcurrencyPolicy: Forbid** to prevent overlapping jobs
6. **Set job history limits** to prevent clutter
7. **Test jobs in staging** before production deployment
8. **Implement graceful degradation** (skip bad records, continue)

### Monitoring

Set up alerts for:
- Job failures: `WorkerJobFailures` alert
- No successful runs in expected timeframe: `ArxivIngestionStalled` alert
- Long-running jobs: Alert if job takes > 1 hour

---

## Escalation

**When to escalate:**
- Multiple consecutive job failures (>3)
- Data pipeline blocked for >4 hours
- Unable to resolve with standard procedures
- Suspected code bug causing failures

**Escalation Path:**
1. Check runbooks and documentation
2. Review recent code changes
3. Contact on-call engineer
4. Engage development team if code fix needed

---

## Related Runbooks

- [Database Rollback](./DATABASE_ROLLBACK.md)
- [GitHub Rate Limit](./GITHUB_RATE_LIMIT.md)
- [API Incident Response](./API_INCIDENT_RESPONSE.md)

---

**Last Reviewed:** November 18, 2025
