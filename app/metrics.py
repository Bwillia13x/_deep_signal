from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "api_requests_total", "API requests", ["path", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds", "API latency", ["path", "method"]
)
