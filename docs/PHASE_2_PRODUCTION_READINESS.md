# Phase 2: Production Readiness - Implementation Guide

## Overview

This document outlines the Phase 2 production readiness enhancements implemented for the DeepTech Radar MVP.

## Completed Features

### API Enhancements

#### 1. API Versioning (`/v1`)
All API endpoints are now prefixed with `/v1` for future-proof API evolution:
- `/v1/papers` - List and search papers
- `/v1/papers/near` - Vector similarity search
- `/v1/repositories` - Repository listings
- `/v1/opportunities` - Investment opportunities
- `/health` - Health check (also available at `/v1/health`)

#### 2. Response Compression
GZip compression is automatically applied to responses larger than 1KB, reducing bandwidth usage by 60-80% for typical JSON responses.

**Configuration:**
```python
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### 3. Advanced Filters on `/v1/papers`

New query parameters for precise filtering:

| Parameter | Type | Description | Range |
|-----------|------|-------------|-------|
| `q` | string | Full-text search on title/abstract | - |
| `domain` | string | Filter by specific domain | - |
| `min_composite_score` | float | Minimum composite score | 0.0-1.0 |
| `min_moat_score` | float | Minimum moat score | 0.0-1.0 |
| `min_scalability_score` | float | Minimum scalability score | 0.0-1.0 |
| `sort_by` | string | Sort field | `id`, `composite_score`, `published_at` |
| `limit` | int | Results per page | 1-100 |
| `offset` | int | Pagination offset | 0+ |

**Example requests:**
```bash
# High composite score papers in quantum domain
curl "http://localhost:8000/v1/papers?domain=quant-ph&min_composite_score=0.7&sort_by=composite_score&limit=10"

# Papers with high moat and scalability
curl "http://localhost:8000/v1/papers?min_moat_score=0.6&min_scalability_score=0.6"

# Recent papers sorted by date
curl "http://localhost:8000/v1/papers?sort_by=published_at&limit=20"
```

#### 4. Structured Error Responses

Error responses now include structured JSON with additional context:

```json
{
  "detail": {
    "error": "not_found",
    "message": "Paper with id 12345 not found or has no embedding",
    "paper_id": 12345
  }
}
```

Error types:
- `missing_parameter` - Required parameter not provided
- `not_found` - Resource not found
- `invalid_input` - Validation failed

### Observability Enhancements

#### 1. Prometheus Alert Rules

Comprehensive alert rules covering:

**Ingestion Alerts:**
- `NoPapersIngestedIn24Hours` - No arXiv papers processed in 24h (Warning)
- `GitHubRateLimitExceeded` - High rate limit hit rate >20% (Warning)
- `ArXivIngestionErrors` - High error rate (Warning)
- `GitHubIngestionErrors` - High error rate (Warning)

**API Alerts:**
- `HighAPIErrorRate` - 5xx errors >1% for 5m (Critical)
- `SlowVectorSearch` - p95 latency >1s for 15m (Warning)
- `SlowAPIResponses` - p95 latency >500ms for 10m (Warning)
- `HighAPIRequestRate` - Unusual traffic spike (Info)

**Database Alerts:**
- `DatabaseConnectionErrors` - Connection failures (Critical)
- `HighDatabaseConnections` - Pool utilization >80% (Warning)

**Worker Alerts:**
- `ScoringJobFailed` - No successful run in 24h (Warning)
- `OpportunitiesJobFailed` - No successful run in 24h (Warning)

**System Alerts:**
- `HighMemoryUsage` - Process memory >4GB (Warning)
- `DiskSpaceLow` - Disk space <10% (Critical)

**Configuration:**
Alert rules are defined in `deploy/monitoring/prometheus-alerts.yml`. Import into Prometheus:

```yaml
# prometheus.yml
rule_files:
  - "prometheus-alerts.yml"
```

#### 2. Enhanced Grafana Dashboards

**Existing Dashboard (Overview):**
- API request rate
- API latency (p50, p95)
- ArXiv papers processed
- GitHub repos processed
- Ingestion errors
- Rate limit tracking

**New Dashboard (API Performance):**
- API request rate by endpoint
- 5xx error rate gauge
- Latency percentiles (p50, p95, p99) by endpoint
- Top 10 endpoints by traffic
- Response status code distribution

**Dashboard Files:**
- `deploy/monitoring/grafana/provisioning/dashboards/deeptech-radar-overview.json`
- `deploy/monitoring/grafana/provisioning/dashboards/deeptech-api-dashboard.json`

**Accessing Dashboards:**
1. Start Grafana: `docker-compose up -d grafana`
2. Open http://localhost:3000
3. Navigate to Dashboards > DeepTech Radar Overview
4. Navigate to Dashboards > DeepTech Radar - API Performance

### API Documentation

Enhanced OpenAPI documentation with:
- Detailed parameter descriptions
- Response schema definitions
- Example values and constraints
- Error response formats

**Access API docs:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Production Deployment Checklist

### Pre-deployment

- [ ] Review and test all alert rules
- [ ] Configure alert notification channels (Slack, PagerDuty, email)
- [ ] Set up Grafana datasources and import dashboards
- [ ] Configure CORS origins for production domains
- [ ] Set environment variables for production (DATABASE_URL, API keys)
- [ ] Review and adjust rate limits if needed

### Deployment

- [ ] Deploy application with GZip middleware enabled
- [ ] Verify `/v1` API endpoints are accessible
- [ ] Test advanced filters with production-like data
- [ ] Confirm Prometheus is scraping `/metrics` endpoint
- [ ] Verify Grafana dashboards display live data
- [ ] Trigger test alerts to validate notification flow

### Post-deployment

- [ ] Monitor API latency for 24 hours
- [ ] Review error rates and investigate any spikes
- [ ] Validate alert thresholds match production traffic patterns
- [ ] Document any threshold adjustments needed
- [ ] Set up on-call rotation for critical alerts

## Performance Baselines

Expected performance targets:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| `/v1/papers` p95 latency | <300ms | >500ms |
| `/v1/papers/near` p95 latency | <500ms | >1s |
| API error rate | <0.1% | >1% |
| Papers ingested/day | >100 | 0 in 24h |
| Database connections | <70% | >80% |

## Monitoring Best Practices

1. **Review dashboards daily** during first week of production
2. **Set up alert routing** to appropriate teams/individuals
3. **Document incident responses** in runbooks
4. **Tune alert thresholds** based on actual traffic patterns
5. **Add custom metrics** for business-specific KPIs
6. **Regular dashboard reviews** to identify trends

## Future Enhancements (Phase 2+ continued)

Remaining Phase 2 items for future implementation:

### Milestone 2.2 (Remaining)
- [ ] ETag caching for conditional requests
- [ ] Rate limiting per IP/API key
- [ ] Cursor-based pagination for large datasets

### Milestone 2.3
- [ ] Performance testing with 50+ RPS
- [ ] Database index optimization
- [ ] Query performance tuning
- [ ] Worker job optimization

### Milestone 2.4
- [ ] Automated backup scripts
- [ ] Disaster recovery procedures
- [ ] Operational runbooks
- [ ] Restore testing

## Support

For issues or questions:
1. Check Grafana dashboards for system health
2. Review Prometheus alerts for active issues
3. Check application logs with structured JSON output
4. Consult DEVELOPMENT_ROADMAP.md for detailed specifications

## Version History

- **v1.0.0** (2025-11-18): Phase 2 production readiness
  - API versioning (/v1)
  - Response compression
  - Advanced filtering
  - Prometheus alerts
  - Enhanced Grafana dashboards
  - Structured error responses
