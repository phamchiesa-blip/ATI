"""API Routers for Gu Phim."""

from server.routers.auth import router as auth_router
from server.routers.movies import router as movies_router
from server.routers.recommendations import router as recommendations_router
from server.routers.tonight import router as tonight_router
from server.routers.evaluation import router as evaluation_router

__all__ = [
    "auth_router",
    "movies_router",
    "recommendations_router",
    "tonight_router",
    "evaluation_router",
]

