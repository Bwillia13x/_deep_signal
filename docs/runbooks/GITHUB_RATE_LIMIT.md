# Runbook: GitHub API Rate Limit Handling

**Severity:** P2 (High)  
**Service:** GitHub Ingestion Worker  
**Last Updated:** November 18, 2025

---

## Overview

This runbook covers handling GitHub API rate limits in the DeepTech Radar system. GitHub enforces rate limits on API requests to ensure fair usage and system stability.

---

## GitHub Rate Limits

### Authenticated Requests

With a Personal Access Token (PAT):
- **5,000 requests per hour** per token
- Resets hourly from the first request
- Check remaining quota via headers or API

### Unauthenticated Requests

Without a token (not recommended for production):
- **60 requests per hour** per IP address
- Very limited, not suitable for our use case

### GraphQL API

- **5,000 points per hour** (different from REST API quota)
- Each query costs different points based on complexity

---

## Detecting Rate Limit Issues

### Symptoms

- GitHub worker jobs failing
- 403 Forbidden responses in logs
- Prometheus alert: `GitHubRateLimitExhausted`
- API response headers show 0 remaining requests

### Check Rate Limit Status

#### From Logs

```bash
# Check worker logs for rate limit errors
kubectl logs -n <namespace> -l app=github-worker --tail=100 | grep -i "rate limit"

# Look for patterns like:
# "GitHub API rate limit exceeded"
# "403 Forbidden: API rate limit exceeded"
# "X-RateLimit-Remaining: 0"
```

#### Using API Directly

```bash
# Check current rate limit status
curl -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/rate_limit

# Example response:
# {
#   "resources": {
#     "core": {
#       "limit": 5000,
#       "remaining": 0,
#       "reset": 1699564800,  # Unix timestamp
#       "used": 5000
#     },
#     ...
#   }
# }
```

#### From Response Headers

Every GitHub API response includes rate limit headers:
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4850
X-RateLimit-Reset: 1699564800
X-RateLimit-Used: 150
```

---

## Immediate Response

### Step 1: Assess Impact

```bash
# Check when rate limit resets
curl -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/rate_limit | jq '.resources.core.reset'

# Convert Unix timestamp to readable time
date -d @<timestamp>
# Example: "Mon Nov 18 16:00:00 UTC 2025"

# Calculate time until reset
RESET_TIME=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/rate_limit | jq '.resources.core.reset')
CURRENT_TIME=$(date +%s)
WAIT_SECONDS=$((RESET_TIME - CURRENT_TIME))
echo "Wait time: $((WAIT_SECONDS / 60)) minutes"
```

### Step 2: Suspend GitHub Worker

Temporarily suspend the GitHub ingestion worker:

```bash
# Suspend CronJob
kubectl patch cronjob github-hourly -n <namespace> -p '{"spec":{"suspend":true}}'

# Verify suspension
kubectl get cronjob github-hourly -n <namespace>
# Output should show SUSPEND: True
```

### Step 3: Wait for Reset

Option A: **Wait for automatic reset** (recommended for one-time issues)
```bash
# Wait until reset time
sleep ${WAIT_SECONDS}

# Verify quota restored
curl -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/rate_limit | jq '.resources.core.remaining'
```

Option B: **Continue with reduced capacity** (if critical)
- Reduce ingestion scope
- Implement more aggressive caching
- Switch to secondary token (if available)

---

## Long-Term Solutions

### Solution 1: Reduce Request Volume

#### Optimize Worker Configuration

```bash
# Edit ConfigMap to reduce ingestion scope
kubectl edit configmap deeptech-config -n <namespace>
```

Update values:
```yaml
data:
  GITHUB_LOOKBACK_DAYS: "3"  # Reduced from 7
  GITHUB_MAX_REPOS: "250"    # Reduced from 500
```

```bash
# Resume worker with new settings
kubectl patch cronjob github-hourly -n <namespace> -p '{"spec":{"suspend":false}}'
```

#### Reduce CronJob Frequency

```bash
# Edit CronJob schedule
kubectl edit cronjob github-hourly -n <namespace>

# Change schedule from hourly to every 2 hours:
# Before: schedule: "15 * * * *"
# After:  schedule: "15 */2 * * *"

# Or every 4 hours:
# schedule: "15 */4 * * *"
```

### Solution 2: Implement Request Batching

Optimize the worker code to batch API requests:

**Code changes needed in `app/workers/github_hourly.py`:**

```python
# Before: Multiple API calls per repo
def fetch_repo_details(repo_name):
    repo_data = github_client.get_repo(repo_name)
    readme = github_client.get_readme(repo_name)
    languages = github_client.get_languages(repo_name)
    return repo_data, readme, languages

# After: Single GraphQL query for multiple repos
def fetch_repos_batch(repo_names):
    query = """
    query($repos: [String!]!) {
      repositories(names: $repos) {
        name
        description
        stargazerCount
        readme
        languages {
          name
          percentage
        }
      }
    }
    """
    return github_client.graphql(query, repos=repo_names)
```

### Solution 3: Use Multiple GitHub Tokens

Rotate between multiple tokens to effectively multiply rate limit:

#### Create Additional Tokens

1. Create 2-3 additional GitHub Personal Access Tokens
2. Store in Kubernetes secrets

```bash
# Update secret with multiple tokens
kubectl create secret generic github-tokens \
  --from-literal=token-1="${GITHUB_TOKEN_1}" \
  --from-literal=token-2="${GITHUB_TOKEN_2}" \
  --from-literal=token-3="${GITHUB_TOKEN_3}" \
  --namespace=<namespace> \
  --dry-run=client -o yaml | kubectl apply -f -
```

#### Implement Token Rotation in Code

**Update `app/workers/github_hourly.py`:**

```python
import os
import random

# Load all tokens
GITHUB_TOKENS = [
    os.getenv("GITHUB_TOKEN_1"),
    os.getenv("GITHUB_TOKEN_2"),
    os.getenv("GITHUB_TOKEN_3"),
]

def get_token_with_quota():
    """Return token with most remaining quota."""
    best_token = None
    max_remaining = 0
    
    for token in GITHUB_TOKENS:
        resp = requests.get(
            "https://api.github.com/rate_limit",
            headers={"Authorization": f"token {token}"}
        )
        remaining = resp.json()["resources"]["core"]["remaining"]
        if remaining > max_remaining:
            max_remaining = remaining
            best_token = token
    
    return best_token if max_remaining > 100 else None
```

### Solution 4: Implement Aggressive Caching

Cache GitHub API responses to reduce duplicate requests:

**Update database schema:**
```sql
CREATE TABLE IF NOT EXISTS github_api_cache (
    endpoint VARCHAR(500) PRIMARY KEY,
    response_data JSONB NOT NULL,
    cached_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cache_expires ON github_api_cache(expires_at);
```

**Implement cache layer:**
```python
def get_cached_or_fetch(endpoint, ttl_hours=24):
    """Get from cache or fetch from API."""
    # Check cache
    cached = db.query(GitHubAPICache).filter_by(endpoint=endpoint).first()
    if cached and cached.expires_at > datetime.utcnow():
        return cached.response_data
    
    # Fetch from API
    response = github_client.get(endpoint)
    
    # Store in cache
    db.merge(GitHubAPICache(
        endpoint=endpoint,
        response_data=response.json(),
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours)
    ))
    db.commit()
    
    return response.json()
```

### Solution 5: Use Conditional Requests

Use ETags to avoid fetching unchanged resources:

```python
def fetch_with_etag(url, last_etag=None):
    """Fetch resource using ETag for conditional request."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    if last_etag:
        headers["If-None-Match"] = last_etag
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 304:
        # Not modified, no quota used!
        return None, last_etag
    
    new_etag = response.headers.get("ETag")
    return response.json(), new_etag
```

---

## Monitoring

### Prometheus Metrics

Add rate limit tracking metrics:

```python
from prometheus_client import Gauge

github_rate_limit_remaining = Gauge(
    'github_rate_limit_remaining',
    'Remaining GitHub API requests'
)

github_rate_limit_reset_timestamp = Gauge(
    'github_rate_limit_reset_timestamp',
    'Unix timestamp when rate limit resets'
)

def update_rate_limit_metrics():
    """Update Prometheus metrics with current rate limit status."""
    resp = requests.get(
        "https://api.github.com/rate_limit",
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    )
    data = resp.json()["resources"]["core"]
    
    github_rate_limit_remaining.set(data["remaining"])
    github_rate_limit_reset_timestamp.set(data["reset"])
```

### Prometheus Alerts

Add alert for low quota:

```yaml
# deploy/monitoring/prometheus-alerts.yml
groups:
  - name: github_alerts
    rules:
      - alert: GitHubRateLimitLow
        expr: github_rate_limit_remaining < 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GitHub API rate limit running low"
          description: "Only {{ $value }} requests remaining"
      
      - alert: GitHubRateLimitExhausted
        expr: github_rate_limit_remaining == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "GitHub API rate limit exhausted"
          description: "No requests remaining until reset"
```

### Dashboard Panel

Add to Grafana dashboard:

```json
{
  "title": "GitHub Rate Limit",
  "targets": [
    {
      "expr": "github_rate_limit_remaining",
      "legendFormat": "Remaining Requests"
    }
  ],
  "type": "graph"
}
```

---

## Prevention

### Best Practices

1. **Track quota proactively** - Monitor remaining requests
2. **Cache aggressively** - Avoid duplicate API calls
3. **Use conditional requests** - Leverage ETags
4. **Batch requests** - Use GraphQL when possible
5. **Implement backoff** - Slow down when quota low
6. **Use webhooks** - For real-time updates instead of polling
7. **Multiple tokens** - Distribute load across tokens
8. **Optimize queries** - Fetch only needed fields

### Worker Code Best Practices

```python
def ingest_github_repos():
    """Ingest GitHub repos with rate limit awareness."""
    # Check quota before starting
    quota = check_rate_limit()
    if quota["remaining"] < 100:
        logger.warning(f"Low quota ({quota['remaining']}), skipping run")
        return
    
    # Adjust batch size based on quota
    max_repos = min(
        config.GITHUB_MAX_REPOS,
        quota["remaining"] // 5  # Assume 5 requests per repo
    )
    
    # Process repos
    for repo in fetch_repos(limit=max_repos):
        # Check quota every 100 repos
        if repo.index % 100 == 0:
            quota = check_rate_limit()
            if quota["remaining"] < 50:
                logger.warning("Quota running low, stopping early")
                break
        
        process_repo(repo)
```

---

## Emergency Contacts

- **GitHub Support**: https://support.github.com/ (for quota increase requests)
- **Rate Limit Appeal**: For legitimate high-volume use cases, contact GitHub to request higher limits

---

## Related Runbooks

- [Worker Failure](./WORKER_FAILURE.md)
- [API Incident Response](./API_INCIDENT_RESPONSE.md)

---

**Last Reviewed:** November 18, 2025
