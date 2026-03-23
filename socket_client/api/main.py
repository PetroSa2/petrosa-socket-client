"""
FastAPI application entry point for Socket Client Configuration API.

Provides runtime configuration management for WebSocket streams, reconnection, and circuit breaker.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from socket_client.api.routes import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Socket Client Configuration API")
    yield
    # Shutdown
    logger.info("Shutting down Socket Client Configuration API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Petrosa Socket Client Configuration API",
        description="Runtime configuration for WebSocket streams, reconnection, and circuit breaker",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(config.router, prefix="/api/v1", tags=["Configuration"])

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "Socket Client Configuration API",
            "version": "1.0.0",
            "endpoints": [
                "/api/v1/config/streams",
                "/api/v1/config/reconnection",
                "/api/v1/config/circuit-breaker",
                "/api/v1/config/validate",
                "/docs",
            ],
        }

    @app.get("/healthz")
    async def healthz():
        """Liveness probe endpoint."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready():
        """Readiness probe endpoint."""
        return {"status": "ready"}

    return app


# Create app instance
app = create_app()
