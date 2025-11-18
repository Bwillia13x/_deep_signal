from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes.health import router as health_router
from app.api.routes.opportunities import router as opp_router
from app.api.routes.papers import router as papers_router
from app.api.routes.repositories import router as repos_router
from app.config import settings
from app.logging_config import configure_logging
from app.middleware.prometheus import PrometheusMiddleware
from app.middleware.request_id import RequestIdMiddleware

app = FastAPI(
    title="DeepTech Radar API",
    version="1.0.0",
    description="Production-ready DeepTech opportunity discovery and analysis API",
    docs_url="/docs",
    redoc_url="/redoc",
)

configure_logging(settings.log_level)

# Add compression middleware (applies to responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add metrics and request tracking
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestIdMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /v1 prefix for API versioning
app.include_router(health_router, prefix="/v1")
app.include_router(papers_router, prefix="/v1")
app.include_router(repos_router, prefix="/v1")
app.include_router(opp_router, prefix="/v1")

# Keep health check at root for load balancers
app.include_router(health_router)


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
