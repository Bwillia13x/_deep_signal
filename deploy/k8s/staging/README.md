# Staging Deployment - Quick Start

This directory contains all Kubernetes manifests needed to deploy DeepTech Radar to a staging environment.

## Prerequisites

1. **kubectl** installed and configured
2. Access to a Kubernetes cluster
3. Required credentials:
   - `DATABASE_URL` - PostgreSQL connection string with pgvector
   - `OPENAI_API_KEY` - OpenAI API key for embeddings
   - `GITHUB_TOKEN` - GitHub Personal Access Token

## Quick Deploy

### Option 1: Automated Deployment (Recommended)

```bash
# Export required environment variables
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/deeptech_staging"
export OPENAI_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."

# Run deployment script from project root
./scripts/deploy_staging.sh
```

This script will:
- Create the `deeptech-staging` namespace
- Create secrets from environment variables
- Deploy API service (2 replicas)
- Deploy all 5 worker CronJobs
- Wait for services to be ready
- Show deployment status

### Option 2: Manual Deployment

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Create secrets
kubectl create secret generic deeptech-secrets \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=openai-api-key="${OPENAI_API_KEY}" \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --namespace=deeptech-staging

# 3. Apply ConfigMap
kubectl apply -f configmap.yaml

# 4. Deploy API
kubectl apply -f api-deployment.yaml
kubectl apply -f api-service.yaml
kubectl apply -f api-ingress.yaml

# 5. Deploy CronJobs
kubectl apply -f cronjobs.yaml

# 6. Verify deployment
kubectl get pods -n deeptech-staging
kubectl get svc -n deeptech-staging
kubectl get cronjobs -n deeptech-staging
```

## Verify Deployment

### Check Pod Status

```bash
kubectl get pods -n deeptech-staging
```

Expected output:
```
NAME                            READY   STATUS    RESTARTS   AGE
deeptech-api-xxxx-xxxx         1/1     Running   0          2m
deeptech-api-yyyy-yyyy         1/1     Running   0          2m
```

### Test API Health

```bash
# Port-forward for local testing
kubectl port-forward -n deeptech-staging svc/deeptech-api 8000:8000

# In another terminal, check health
curl http://localhost:8000/health
```

### Run Automated Validation

```bash
# From project root
python scripts/validate_staging.py --url http://localhost:8000
```

## Files Overview

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates `deeptech-staging` namespace |
| `configmap.yaml` | Configuration for workers and API |
| `secrets.yaml` | Template for secrets (DO NOT commit actual values) |
| `api-deployment.yaml` | API deployment with 2 replicas |
| `api-service.yaml` | ClusterIP service for API |
| `api-ingress.yaml` | Ingress configuration (update domain) |
| `cronjobs.yaml` | All 5 worker CronJobs |

## Worker CronJobs

The deployment includes 5 scheduled workers:

| Worker | Schedule | Description |
|--------|----------|-------------|
| `arxiv-hourly` | Every hour at :00 | Ingest papers from arXiv |
| `github-hourly` | Every hour at :15 | Ingest repositories from GitHub |
| `linking-daily` | Daily at 02:30 UTC | Link papers to repositories |
| `scoring-daily` | Daily at 03:00 UTC | Calculate 6D scores |
| `opportunities-daily` | Daily at 03:30 UTC | Generate investment opportunities |

## Trigger Manual Job

```bash
# Create a one-time job from a CronJob
kubectl create job --from=cronjob/arxiv-hourly arxiv-manual-test -n deeptech-staging

# Watch job progress
kubectl get jobs -n deeptech-staging -w

# Check logs
kubectl logs job/arxiv-manual-test -n deeptech-staging
```

## Configuration

Edit `configmap.yaml` to adjust:
- Log level
- Worker batch sizes
- Lookback periods
- Resource limits

After editing, apply changes:
```bash
kubectl apply -f configmap.yaml
kubectl rollout restart deployment/deeptech-api -n deeptech-staging
```

## Monitoring

### View Logs

```bash
# API logs
kubectl logs -n deeptech-staging -l app=deeptech-api --tail=100 -f

# Specific worker job logs
kubectl logs -n deeptech-staging job/<job-name>
```

### Resource Usage

```bash
kubectl top pods -n deeptech-staging
```

### Metrics

```bash
# Port-forward and access metrics
kubectl port-forward -n deeptech-staging svc/deeptech-api 8000:8000
curl http://localhost:8000/metrics
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n deeptech-staging

# Describe pod for events
kubectl describe pod <pod-name> -n deeptech-staging

# Check logs
kubectl logs <pod-name> -n deeptech-staging
```

### Common Issues

1. **ImagePullBackOff**: Update image name in deployment YAML
2. **CrashLoopBackOff**: Check logs for errors, verify DATABASE_URL
3. **Pending Pods**: Check cluster resources with `kubectl describe nodes`

See detailed troubleshooting in [DEPLOYMENT_GUIDE.md](../../docs/DEPLOYMENT_GUIDE.md)

## Cleanup

```bash
# Delete all resources in namespace
kubectl delete namespace deeptech-staging

# Or delete individual components
kubectl delete -f .
```

## Next Steps

1. ✅ Deploy to staging (you are here)
2. Run full validation checklist: [VALIDATION_CHECKLIST.md](../../docs/VALIDATION_CHECKLIST.md)
3. Monitor for 48+ hours
4. Run end-to-end pipeline test
5. Prepare for production deployment

## Documentation

- **[Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md)**: Complete deployment instructions
- **[Validation Checklist](../../docs/VALIDATION_CHECKLIST.md)**: Validation procedures
- **[Runbooks](../../docs/runbooks/)**: Incident response guides

## Support

For issues, check:
1. [Deployment Guide](../../docs/DEPLOYMENT_GUIDE.md#troubleshooting)
2. [Runbooks](../../docs/runbooks/) for specific scenarios
3. Pod logs and events

---

**Created:** November 18, 2025  
**Environment:** Staging  
**Namespace:** deeptech-staging
