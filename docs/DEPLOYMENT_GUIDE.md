# DeepTech Radar - Deployment Guide

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Environments:** Staging, Production

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Validation](#validation)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide provides comprehensive instructions for deploying the DeepTech Radar application to Kubernetes environments. The system consists of:

- **API Service**: FastAPI application serving REST endpoints
- **Worker CronJobs**: 5 scheduled jobs for data ingestion and processing
  - arXiv Hourly: Paper ingestion from arXiv
  - GitHub Hourly: Repository ingestion from GitHub
  - Linking Daily: Link papers to repositories
  - Scoring Daily: Calculate 6D scores for papers
  - Opportunities Daily: Generate investment opportunities

### Architecture

```
┌─────────────────┐
│   Ingress       │
│  (nginx/traefik)│
└────────┬────────┘
         │
    ┌────▼────┐
    │   API   │ (2 replicas)
    │ Service │
    └────┬────┘
         │
    ┌────▼──────────┐
    │  PostgreSQL   │
    │  + pgvector   │
    └───────────────┘

Worker CronJobs (scheduled):
├── arXiv Hourly (every hour)
├── GitHub Hourly (every hour at :15)
├── Linking Daily (02:30 UTC)
├── Scoring Daily (03:00 UTC)
└── Opportunities Daily (03:30 UTC)
```

---

## Prerequisites

### Required Tools

1. **kubectl** (v1.24+)
   ```bash
   kubectl version --client
   ```

2. **Access to Kubernetes Cluster**
   - Verify connection: `kubectl cluster-info`
   - Ensure you have permissions to create namespaces, deployments, secrets

3. **Docker Images**
   - API image: `ghcr.io/yourorg/deeptech-radar-api:latest`
   - Worker image: `ghcr.io/yourorg/deeptech-radar-worker:latest`
   
   Update image references in manifests if using different registry.

### Required Credentials

Before deployment, you need:

1. **Database URL**
   ```
   postgresql+psycopg://user:password@host:5432/database_name
   ```
   - Database must have pgvector extension installed
   - Schema should be initialized with Alembic migrations

2. **OpenAI API Key**
   ```
   sk-proj-...
   ```
   - Used for embeddings generation
   - Ensure sufficient quota/credits

3. **GitHub Personal Access Token**
   ```
   ghp_...
   ```
   - Scopes needed: `public_repo`, `read:org`
   - For accessing GitHub API

### Environment Setup

Export required environment variables:

```bash
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/deeptech_staging"
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."
```

---

## Staging Deployment

### Quick Start

The fastest way to deploy to staging:

```bash
# Set environment variables (see above)
export DATABASE_URL="..."
export OPENAI_API_KEY="..."
export GITHUB_TOKEN="..."

# Run deployment script
./scripts/deploy_staging.sh
```

This script will:
1. Create the `deeptech-staging` namespace
2. Create secrets from environment variables
3. Apply ConfigMap
4. Deploy API service (2 replicas)
5. Deploy all 5 CronJobs
6. Wait for API pods to be ready
7. Display deployment status

### Manual Deployment Steps

If you prefer manual control:

#### Step 1: Create Namespace

```bash
kubectl apply -f deploy/k8s/staging/namespace.yaml
```

#### Step 2: Create Secrets

```bash
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=openai-api-key="${OPENAI_API_KEY}" \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --namespace=deeptech-staging
```

**Security Note:** Never commit actual secrets to version control. The `secrets.yaml` file is a template only.

#### Step 3: Apply ConfigMap

```bash
kubectl apply -f deploy/k8s/staging/configmap.yaml
```

#### Step 4: Deploy API Service

```bash
kubectl apply -f deploy/k8s/staging/api-deployment.yaml
kubectl apply -f deploy/k8s/staging/api-service.yaml
kubectl apply -f deploy/k8s/staging/api-ingress.yaml
```

#### Step 5: Deploy CronJobs

```bash
kubectl apply -f deploy/k8s/staging/cronjobs.yaml
```

#### Step 6: Verify Deployment

```bash
# Check pod status
kubectl get pods -n deeptech-staging

# Check services
kubectl get svc -n deeptech-staging

# Check ingress
kubectl get ingress -n deeptech-staging

# Check cronjobs
kubectl get cronjobs -n deeptech-staging
```

### Database Initialization

Before first deployment, ensure database is initialized:

```bash
# Run migrations (from a pod or locally)
kubectl exec -it deployment/deeptech-api -n deeptech-staging -- alembic upgrade head
```

---

## Production Deployment

Production deployment follows the same process as staging, with key differences:

### Differences from Staging

1. **Namespace**: Use `deeptech-production` instead of `deeptech-staging`
2. **Replicas**: Consider scaling API to 3+ replicas
3. **Resources**: Increase resource limits based on load testing
4. **Domain**: Update ingress hostname
5. **Monitoring**: Ensure production Prometheus/Grafana are configured
6. **Backups**: Ensure automated backups are configured

### Production Checklist

Before deploying to production:

- [ ] Staging has been stable for 7+ days
- [ ] All tests passing (38/39 minimum)
- [ ] Performance baselines met (see VALIDATION_CHECKLIST.md)
- [ ] Backup and restore procedures tested
- [ ] Monitoring and alerting configured
- [ ] Runbooks prepared (see docs/runbooks/)
- [ ] Rollback plan documented
- [ ] Team trained on operational procedures
- [ ] DNS configured for production domain
- [ ] SSL/TLS certificates configured

### Production Deployment Steps

```bash
# Create production manifests (copy from staging, update namespace)
mkdir -p deploy/k8s/production
cp -r deploy/k8s/staging/* deploy/k8s/production/

# Update namespace in all files
sed -i 's/deeptech-staging/deeptech-production/g' deploy/k8s/production/*.yaml

# Set production credentials
export DATABASE_URL="postgresql+psycopg://user:pass@prod-host:5432/deeptech_production"
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."

# Deploy
kubectl apply -f deploy/k8s/production/namespace.yaml
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=openai-api-key="${OPENAI_API_KEY}" \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --namespace=deeptech-production
kubectl apply -f deploy/k8s/production/configmap.yaml
kubectl apply -f deploy/k8s/production/api-deployment.yaml
kubectl apply -f deploy/k8s/production/api-service.yaml
kubectl apply -f deploy/k8s/production/api-ingress.yaml
kubectl apply -f deploy/k8s/production/cronjobs.yaml
```

---

## Validation

### Automated Validation

Use the validation script to check deployment health:

```bash
# For local port-forward
kubectl port-forward -n deeptech-staging svc/deeptech-api 8000:8000 &
python scripts/validate_staging.py --url http://localhost:8000

# For ingress-exposed endpoint
python scripts/validate_staging.py --url https://staging.deeptech-radar.example.com
```

The script validates:
- Health endpoint
- All API endpoints (/v1/papers, /v1/papers/near, /v1/repositories, /v1/opportunities)
- Metrics endpoint
- GZip compression

### Manual Validation

#### Check Pod Health

```bash
kubectl get pods -n deeptech-staging
kubectl describe pod <pod-name> -n deeptech-staging
kubectl logs <pod-name> -n deeptech-staging
```

#### Test API Endpoints

```bash
# Port-forward for local testing
kubectl port-forward -n deeptech-staging svc/deeptech-api 8000:8000

# Health check
curl http://localhost:8000/health

# List papers
curl http://localhost:8000/v1/papers?limit=5

# Vector search
curl "http://localhost:8000/v1/papers/near?text_query=quantum+computing&k=5"

# Metrics
curl http://localhost:8000/metrics
```

#### Trigger Manual Job

Test a worker job manually:

```bash
# Create a one-time job from CronJob
kubectl create job --from=cronjob/arxiv-hourly arxiv-manual-test -n deeptech-staging

# Watch job status
kubectl get jobs -n deeptech-staging -w

# Check job logs
kubectl logs job/arxiv-manual-test -n deeptech-staging
```

### Performance Testing

Run basic load test:

```bash
# Using Apache Bench (install with: apt-get install apache2-utils)
ab -n 1000 -c 10 http://localhost:8000/v1/papers?limit=10

# Expected results:
# - P95 latency < 300ms
# - No errors
# - Successful completion of all requests
```

---

## Monitoring

### Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`. Key metrics:

- `api_requests_total{method, endpoint, status}` - Request counter
- `api_request_duration_seconds{method, endpoint}` - Request latency histogram
- `ingest_arxiv_papers_processed_total` - Papers ingested counter
- `ingest_github_repos_processed_total` - Repositories ingested counter

### Grafana Dashboards

Import the included Grafana dashboards:

1. **Overview Dashboard**: `deploy/monitoring/grafana/dashboards/overview.json`
2. **API Performance Dashboard**: `deploy/monitoring/grafana/dashboards/api-performance.json`

### Prometheus Alerts

Alert rules are defined in `deploy/monitoring/prometheus-alerts.yml`:

- HighErrorRate: >5% error rate for 5 minutes
- SlowAPIRequests: P95 > 500ms
- ArxivIngestionStalled: No papers ingested in 2 hours
- DatabaseConnectionFailures: Connection failures detected
- WorkerJobFailures: CronJob failures

### Log Aggregation

View logs from all API pods:

```bash
# All API pods
kubectl logs -n deeptech-staging -l app=deeptech-api --tail=100 -f

# Specific pod
kubectl logs -n deeptech-staging <pod-name> -f

# Previous container (after crash)
kubectl logs -n deeptech-staging <pod-name> --previous
```

---

## Troubleshooting

### Common Issues

#### Pods Not Starting

**Symptoms:** Pods in CrashLoopBackOff or ImagePullBackOff state

**Diagnosis:**
```bash
kubectl describe pod <pod-name> -n deeptech-staging
kubectl logs <pod-name> -n deeptech-staging
```

**Common Causes:**
1. Image pull failure: Check image name and registry access
2. Database connection failure: Verify DATABASE_URL secret
3. Missing dependencies: Check Dockerfile and requirements

**Solution:** See runbook: `docs/runbooks/API_INCIDENT_RESPONSE.md`

#### Database Connection Failures

**Symptoms:** API returns 500 errors, logs show "connection refused"

**Diagnosis:**
```bash
# Test connection from pod
kubectl exec -it <pod-name> -n deeptech-staging -- bash
psql "${DATABASE_URL}"
```

**Common Causes:**
1. Wrong DATABASE_URL
2. Database server down
3. Network policies blocking access
4. Firewall rules

**Solution:** See runbook: `docs/runbooks/DATABASE_ROLLBACK.md`

#### Worker Jobs Not Running

**Symptoms:** CronJobs scheduled but not executing

**Diagnosis:**
```bash
kubectl get cronjobs -n deeptech-staging
kubectl get jobs -n deeptech-staging
kubectl describe cronjob <cronjob-name> -n deeptech-staging
```

**Common Causes:**
1. Incorrect cron schedule
2. ConcurrencyPolicy preventing execution
3. Job backoff limit reached
4. Resource constraints

**Solution:** See runbook: `docs/runbooks/WORKER_FAILURE.md`

#### GitHub Rate Limiting

**Symptoms:** GitHub ingestion worker failing with 403 errors

**Diagnosis:**
```bash
kubectl logs job/<github-job-name> -n deeptech-staging | grep "rate limit"
```

**Solution:** See runbook: `docs/runbooks/GITHUB_RATE_LIMIT.md`

---

## Rollback Procedures

### Rolling Back API Deployment

If new API version has issues:

```bash
# Rollback to previous version
kubectl rollout undo deployment/deeptech-api -n deeptech-staging

# Check rollback status
kubectl rollout status deployment/deeptech-api -n deeptech-staging

# View rollout history
kubectl rollout history deployment/deeptech-api -n deeptech-staging
```

### Rolling Back Database Migrations

If database migration causes issues:

```bash
# Rollback one migration
kubectl exec -it deployment/deeptech-api -n deeptech-staging -- alembic downgrade -1

# Rollback to specific version
kubectl exec -it deployment/deeptech-api -n deeptech-staging -- alembic downgrade <revision>
```

**Important:** Always test rollback procedures in staging first.

See detailed procedures: `docs/runbooks/DATABASE_ROLLBACK.md`

---

## Additional Resources

- [Phase 2 Production Readiness Guide](./PHASE_2_PRODUCTION_READINESS.md)
- [Validation Checklist](./VALIDATION_CHECKLIST.md)
- [Runbooks](./runbooks/)
- [Development Roadmap](../DEVELOPMENT_ROADMAP.md)
- [Next Session Instructions](../NEXT_SESSION_INSTRUCTIONS.md)

---

## Support

For issues or questions:
1. Check runbooks in `docs/runbooks/`
2. Review troubleshooting section above
3. Check application logs
4. Review Grafana dashboards for metrics

---

**Last Updated:** November 18, 2025
