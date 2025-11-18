from prometheus_client import Counter, Histogram

# API Metrics
REQUEST_COUNT = Counter(
    "api_requests_total", "API requests", ["path", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds", "API latency", ["path", "method"]
)

# ArXiv Worker Metrics
ARXIV_REQUESTS_TOTAL = Counter(
    "ingest_arxiv_requests_total",
    "Total arXiv API requests made",
    ["category", "status"]
)
ARXIV_PAPERS_PROCESSED = Counter(
    "ingest_arxiv_papers_processed_total",
    "Total papers processed from arXiv",
    ["category", "status"]
)
ARXIV_ERRORS = Counter(
    "ingest_arxiv_errors_total",
    "Total errors during arXiv ingestion",
    ["category", "error_type"]
)

# GitHub Worker Metrics
GITHUB_REQUESTS_TOTAL = Counter(
    "ingest_github_requests_total",
    "Total GitHub API requests made",
    ["endpoint", "status"]
)
GITHUB_REPOS_PROCESSED = Counter(
    "ingest_github_repos_processed_total",
    "Total repositories processed from GitHub",
    ["query", "status"]
)
GITHUB_RATE_LIMIT_HITS = Counter(
    "ingest_github_rate_limit_hits_total",
    "Total GitHub rate limit hits"
)
GITHUB_ERRORS = Counter(
    "ingest_github_errors_total",
    "Total errors during GitHub ingestion",
    ["error_type"]
)
