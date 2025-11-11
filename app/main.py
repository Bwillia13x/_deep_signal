from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes.health import router as health_router
from app.api.routes.opportunities import router as opp_router
from app.api.routes.papers import router as papers_router
from app.api.routes.repositories import router as repos_router
from app.config import settings
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware

app = FastAPI(title="DeepTech Radar", version="0.1.0")

configure_logging(settings.log_level)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(papers_router)
app.include_router(repos_router)
app.include_router(opp_router)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
