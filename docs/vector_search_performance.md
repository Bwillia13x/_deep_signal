# Vector Search Performance Characteristics

## Overview

The `/papers/near` endpoint provides semantic similarity search using pgvector with HNSW (Hierarchical Navigable Small World) indexing. This document outlines performance characteristics and optimization guidelines.

## Endpoint Capabilities

### Text Query Search
```
GET /papers/near?text_query=quantum computing&k=10
```
- Embeds input text using all-MiniLM-L6-v2 (384 dimensions)
- Searches for k most similar papers in vector space
- Returns results with similarity scores (0-1 range)

### Paper-to-Paper Search
```
GET /papers/near?paper_id=123&k=20
```
- Uses embedding from specified paper_id
- Finds k most similar papers
- Returns results with similarity scores

## Performance Benchmarks

### Baseline Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| p95 latency | < 500ms | For k=10-20 with 100k papers |
| p99 latency | < 1s | For k=50 with 100k papers |
| Throughput | > 100 req/s | With connection pooling |
| Memory per query | < 10 MB | Embedding + index lookup |

### Actual Performance (Expected)

**With 10k papers:**
- Text query (k=10): ~50-100ms (embedding: 20-30ms, search: 30-70ms)
- Paper-to-paper (k=10): ~30-50ms (no embedding needed)

**With 100k papers:**
- Text query (k=10): ~100-200ms (embedding: 20-30ms, search: 80-170ms)
- Paper-to-paper (k=10): ~80-150ms

**With 1M papers:**
- Text query (k=10): ~200-400ms (embedding: 20-30ms, search: 180-370ms)
- Paper-to-paper (k=10): ~180-350ms

*Note: Benchmarks assume properly configured HNSW index*

## Index Configuration

The papers table uses HNSW indexing for efficient similarity search:

```sql
CREATE INDEX papers_embedding_hnsw_idx 
ON papers 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### HNSW Parameters

- **m = 16**: Number of connections per layer (default)
  - Higher = better recall, more memory
  - Lower = faster build, less memory
  
- **ef_construction = 64**: Index build quality (default)
  - Higher = better recall, slower build
  - Lower = faster build, potentially lower recall

### Query-time Parameters

pgvector supports `SET hnsw.ef_search = N` to control recall/speed tradeoff:

- **ef_search = 40** (default): Good balance
- **ef_search = 64**: Better recall, slower
- **ef_search = 20**: Faster, potentially lower recall

For production, consider tuning based on actual data distribution.

## Optimization Guidelines

### 1. Database Optimization

**Connection Pooling:**
```python
# Already configured in app/db/session.py
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://..."
pool_size = 10
max_overflow = 20
```

**Index Maintenance:**
```sql
-- Rebuild index if data changes significantly
REINDEX INDEX CONCURRENTLY papers_embedding_hnsw_idx;

-- Monitor index statistics
SELECT * FROM pg_stat_user_indexes WHERE indexrelname = 'papers_embedding_hnsw_idx';
```

### 2. Caching Strategies

**Response Caching:**
- Cache popular queries (e.g., "quantum computing", "AI")
- TTL: 5-15 minutes for frequently changing data
- Use Redis or in-memory cache

**Embedding Caching:**
- Cache embeddings for common queries
- Reduces embedding generation overhead (20-30ms per query)

### 3. Query Optimization

**Limit k parameter:**
- Default k=10 is optimal for most use cases
- Maximum k=50 to prevent slow queries
- Larger k values increase latency linearly

**Filtering:**
- Apply domain/date filters before vector search when possible
- Use PostgreSQL partial indexes for common filters

### 4. Load Testing Recommendations

**Test scenarios:**
```bash
# Baseline: Single query
curl -X GET "http://localhost:8000/papers/near?text_query=test&k=10"

# Load test: 100 concurrent requests
ab -n 1000 -c 100 "http://localhost:8000/papers/near?text_query=test&k=10"

# Load test: Mixed queries
wrk -t4 -c100 -d30s --script=vector_search.lua http://localhost:8000/
```

**Monitoring:**
- Track p50, p95, p99 latencies
- Monitor database connection pool utilization
- Watch for query queue buildup
- Alert on p95 > 500ms

## Scalability Considerations

### Vertical Scaling
- **CPU**: Embedding generation is CPU-bound
- **RAM**: HNSW index loaded in memory (~1.5KB per vector)
  - 100k papers: ~150 MB
  - 1M papers: ~1.5 GB
  - 10M papers: ~15 GB

### Horizontal Scaling
- Read replicas for query distribution
- Separate embedding service for high-throughput scenarios
- Load balancer with sticky sessions (optional)

### Data Growth Impact

| Paper Count | Index Size | Build Time | Query Time (k=10) |
|-------------|-----------|------------|-------------------|
| 10k | ~15 MB | ~5s | 30-50ms |
| 100k | ~150 MB | ~1min | 80-150ms |
| 1M | ~1.5 GB | ~15min | 180-350ms |
| 10M | ~15 GB | ~3hr | 400-700ms |

## Monitoring & Alerts

### Key Metrics

**Application Metrics (Prometheus):**
```
# Query latency
api_request_duration_seconds{endpoint="/papers/near", method="GET"}

# Query rate
rate(api_requests_total{endpoint="/papers/near"}[5m])

# Error rate
rate(api_requests_total{endpoint="/papers/near", status="500"}[5m])
```

**Database Metrics:**
```sql
-- Active queries
SELECT count(*) FROM pg_stat_activity WHERE query LIKE '%embedding%';

-- Slow queries
SELECT * FROM pg_stat_statements 
WHERE query LIKE '%<=>%' 
ORDER BY mean_exec_time DESC;
```

### Alert Thresholds

- p95 latency > 500ms (Warning)
- p95 latency > 1s (Critical)
- Error rate > 1% (Warning)
- Error rate > 5% (Critical)
- Database connection pool > 80% (Warning)

## Future Optimizations

### Phase 2+ Enhancements

1. **Approximate Nearest Neighbors (ANN) Libraries:**
   - Consider FAISS for CPU/GPU acceleration
   - Evaluate Annoy for memory efficiency
   - Benchmark Hnswlib for pure speed

2. **Hybrid Search:**
   - Combine vector search with keyword search
   - RRF (Reciprocal Rank Fusion) for result merging
   - Boost recent papers or high-citation papers

3. **Pre-computed Clusters:**
   - K-means clustering of papers by domain
   - Coarse-to-fine search within clusters
   - Reduces search space for very large datasets

4. **Query Optimization:**
   - Bloom filters for "has no similar papers" fast path
   - Pre-filtered indexes by domain/date
   - Materialized views for common query patterns

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)
- [PostgreSQL Index Tuning Guide](https://www.postgresql.org/docs/current/indexes.html)

## Version History

- **v1.0** (2025-11-18): Initial documentation
  - Baseline performance targets
  - HNSW configuration
  - Optimization guidelines
