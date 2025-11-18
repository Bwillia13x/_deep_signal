"""API route group utilities."""

from .health import router as health_router
from .opportunities import router as opportunities_router
from .papers import router as papers_router
from .repositories import router as repositories_router

__all__ = [
    "health_router",
    "opportunities_router",
    "papers_router",
    "repositories_router",
]
