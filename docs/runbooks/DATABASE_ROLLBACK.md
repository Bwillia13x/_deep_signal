# Runbook: Database Migration Rollback

**Severity:** P1 (Critical)  
**Service:** PostgreSQL Database  
**Last Updated:** November 18, 2025

---

## Overview

This runbook covers procedures for rolling back database migrations when issues occur. DeepTech Radar uses Alembic for database migrations. Rollback procedures should be tested in staging before production use.

---

## When to Rollback

### Symptoms Indicating Rollback Need

- Application crashes after migration
- Data integrity issues detected
- Performance degradation post-migration
- Missing or corrupted data
- Foreign key constraint violations
- Index creation failures blocking queries

### Risk Assessment

**DO NOT rollback if:**
- Only minor performance issues (optimize instead)
- Issue can be fixed with forward migration
- Data has been written that depends on new schema

**DO rollback if:**
- Application completely broken
- Critical data integrity issues
- Impossible to fix forward due to bad migration
- Rollback tested successfully in staging

---

## Pre-Rollback Checklist

Before proceeding with rollback:

- [ ] **Backup current database state**
  ```bash
  pg_dump "${DATABASE_URL}" > backup_pre_rollback_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Identify target rollback version**
  - Check migration history: `alembic history`
  - Identify the last known good version

- [ ] **Stop all write operations**
  - Suspend worker CronJobs
  - Scale API to 0 replicas (or enable read-only mode)

- [ ] **Document current state**
  - Current revision: `alembic current`
  - Application logs showing errors
  - Database state snapshot

- [ ] **Test rollback in staging first** (CRITICAL)

---

## Rollback Procedures

### Step 1: Stop Write Operations

```bash
# Suspend all CronJobs
kubectl patch cronjob arxiv-hourly -n <namespace> -p '{"spec":{"suspend":true}}'
kubectl patch cronjob github-hourly -n <namespace> -p '{"spec":{"suspend":true}}'
kubectl patch cronjob linking-daily -n <namespace> -p '{"spec":{"suspend":true}}'
kubectl patch cronjob scoring-daily -n <namespace> -p '{"spec":{"suspend":true}}'
kubectl patch cronjob opportunities-daily -n <namespace> -p '{"spec":{"suspend":true}}'

# Scale API to 0 (stops all writes)
kubectl scale deployment/deeptech-api -n <namespace> --replicas=0

# Wait for pods to terminate
kubectl get pods -n <namespace> -w
```

### Step 2: Create Database Backup

```bash
# SSH to a pod with database access or use a dedicated backup pod
kubectl run -it --rm pg-backup \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- bash

# Inside the pod, create backup
pg_dump "${DATABASE_URL}" | gzip > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Copy backup out of pod (in another terminal)
kubectl cp <namespace>/pg-backup:/tmp/backup_*.sql.gz ./backup_pre_rollback.sql.gz
```

**IMPORTANT:** Verify backup is complete and valid before proceeding.

### Step 3: Check Current Migration State

```bash
# Get current migration version
kubectl run -it --rm alembic-check \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic current

# View migration history
kubectl run -it --rm alembic-history \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic history
```

**Example output:**
```
Rev: 0005 (head)
Parent: 0004
Path: alembic/versions/0005_add_scoring_fields.py
```

### Step 4: Execute Rollback

#### Option A: Rollback One Migration

```bash
kubectl run -it --rm alembic-downgrade \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic downgrade -1
```

#### Option B: Rollback to Specific Version

```bash
# Rollback to revision 0004
kubectl run -it --rm alembic-downgrade \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic downgrade 0004
```

#### Option C: Rollback All Migrations (EXTREME - rarely needed)

```bash
kubectl run -it --rm alembic-downgrade \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic downgrade base
```

### Step 5: Verify Rollback

```bash
# Check current version
kubectl run -it --rm alembic-verify \
  --image=ghcr.io/yourorg/deeptech-radar-api:latest \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- alembic current

# Verify database schema
kubectl run -it --rm psql-check \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- psql "${DATABASE_URL}" -c "\dt"

# Check table counts
kubectl run -it --rm psql-count \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- psql "${DATABASE_URL}" -c "
    SELECT 'papers' as table, COUNT(*) FROM papers
    UNION ALL SELECT 'repositories', COUNT(*) FROM repositories
    UNION ALL SELECT 'paper_repo_links', COUNT(*) FROM paper_repo_links
    UNION ALL SELECT 'opportunities', COUNT(*) FROM opportunities;
  "
```

### Step 6: Rollback Application Code

If migration was part of a deployment, rollback to previous version:

```bash
# Rollback API deployment
kubectl rollout undo deployment/deeptech-api -n <namespace>

# Or rollback to specific revision
kubectl rollout undo deployment/deeptech-api -n <namespace> --to-revision=2

# Check rollout status
kubectl rollout status deployment/deeptech-api -n <namespace>
```

### Step 7: Resume Operations

```bash
# Scale API back up
kubectl scale deployment/deeptech-api -n <namespace> --replicas=2

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=deeptech-api -n <namespace> --timeout=180s

# Test API health
kubectl port-forward -n <namespace> svc/deeptech-api 8000:8000 &
curl http://localhost:8000/health

# Resume CronJobs (one at a time, monitor each)
kubectl patch cronjob arxiv-hourly -n <namespace> -p '{"spec":{"suspend":false}}'
# Wait and verify before resuming others...
```

---

## Common Rollback Scenarios

### Scenario 1: Failed Migration During Upgrade

**Symptoms:**
```
alembic.util.exc.CommandError: Target database is not up to date
FAILED: Migration failed at revision 0005
```

**Resolution:**
1. Check error logs to identify which migration failed
2. Manually inspect database state
3. Rollback to last successful version
4. Fix migration script
5. Re-test in staging
6. Re-deploy with fixed migration

### Scenario 2: Data Corruption After Migration

**Symptoms:**
- Null values where they shouldn't be
- Foreign key violations
- Duplicate data
- Missing indexes

**Resolution:**
1. **Stop all operations immediately**
2. Create backup of corrupted state (for analysis)
3. Rollback migration
4. Restore from last known good backup (if data loss is acceptable)
5. Investigate root cause
6. Create data repair migration if needed

### Scenario 3: Performance Degradation Post-Migration

**Symptoms:**
- Slow queries after migration
- Missing indexes
- Table scans where indexes expected

**Resolution:**
1. Analyze query plans:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM papers WHERE domain = 'AI' LIMIT 10;
   ```

2. Check for missing indexes:
   ```sql
   SELECT * FROM pg_indexes WHERE tablename = 'papers';
   ```

3. If critical, rollback and add index creation to migration
4. If minor, create forward migration with indexes

---

## Emergency Database Restore

If rollback fails or data corruption is severe:

### Full Database Restore from Backup

```bash
# 1. Drop current database (DESTRUCTIVE)
kubectl run -it --rm psql-admin \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  -- psql "${ADMIN_DATABASE_URL}" -c "DROP DATABASE deeptech_staging;"

# 2. Recreate database
kubectl run -it --rm psql-admin \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  -- psql "${ADMIN_DATABASE_URL}" -c "CREATE DATABASE deeptech_staging OWNER deeptech;"

# 3. Restore from backup
gunzip -c backup_pre_rollback.sql.gz | \
kubectl run -it --rm psql-restore \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- psql "${DATABASE_URL}"

# 4. Re-enable pgvector extension
kubectl run -it --rm psql-extension \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- psql "${DATABASE_URL}" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Verify restore
kubectl run -it --rm psql-verify \
  --image=postgres:14 \
  --restart=Never \
  --namespace=<namespace> \
  --env="DATABASE_URL=${DATABASE_URL}" \
  -- psql "${DATABASE_URL}" -c "
    SELECT 'papers', COUNT(*) FROM papers
    UNION ALL SELECT 'repositories', COUNT(*) FROM repositories;
  "
```

### Point-in-Time Recovery (if supported by database provider)

For cloud databases (AWS RDS, Google Cloud SQL, Azure Database):

1. Navigate to cloud provider console
2. Select database instance
3. Choose "Restore to point in time"
4. Select timestamp before migration
5. Restore to new instance or in-place
6. Update DATABASE_URL to point to restored instance
7. Restart application

---

## Prevention

### Best Practices

1. **Always test migrations in staging first**
2. **Write reversible migrations** (proper upgrade/downgrade)
3. **Use transactions** where possible
4. **Avoid data transformations** in migrations (use separate scripts)
5. **Create backups** before each migration
6. **Limit migration scope** (one logical change per migration)
7. **Document migration purpose** and risks
8. **Test rollback** as part of migration testing
9. **Monitor performance** after migration
10. **Have rollback plan** ready before deployment

### Migration Checklist

Before running migration in production:

- [ ] Migration tested in local environment
- [ ] Migration tested in staging
- [ ] Rollback tested in staging
- [ ] Backup created
- [ ] Downtime window scheduled (if needed)
- [ ] Team notified
- [ ] Rollback plan documented
- [ ] Monitoring ready

---

## Post-Rollback

After successful rollback:

1. **Analyze root cause** of migration failure
2. **Document incident** for future reference
3. **Update migration script** to fix issues
4. **Re-test in staging** thoroughly
5. **Schedule new deployment** when ready
6. **Communicate** to team and stakeholders

---

## Escalation

**When to escalate:**
- Unable to rollback after 2 attempts
- Data corruption cannot be fixed
- Backup restore fails
- Production down for >2 hours

**Escalation Path:**
1. Database administrator
2. Senior backend engineer
3. CTO/Engineering lead
4. Engage database vendor support (if applicable)

---

## Related Runbooks

- [Worker Failure](./WORKER_FAILURE.md)
- [API Incident Response](./API_INCIDENT_RESPONSE.md)

---

**Last Reviewed:** November 18, 2025
