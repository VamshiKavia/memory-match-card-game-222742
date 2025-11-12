import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import legacy game routes (kept for compatibility if needed)
from src.api.game_routes import router as game_router
# Import new deterministic-session endpoints
from src.api.seeded_game_routes import router as seeded_router

# Define OpenAPI tags for grouping in Swagger UI
openapi_tags = [
    {"name": "Game", "description": "Memory Flip Card game endpoints."},
    {"name": "Utility", "description": "Utility and health endpoints."},
]

# Create FastAPI application instance that uvicorn uses as entrypoint (src.api.main:app)
app = FastAPI(
    title="Memory Flip Card Game API",
    description="Backend API for a Memory Flip Card game with in-memory session management.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Configure CORS from environment with safe defaults
# Env precedence:
# - BACKEND_CORS_ORIGINS: comma-separated list of allowed origins
# - REACT_APP_FRONTEND_URL: single allowed origin
# - Defaults include localhost frontend ports for dev and '*' as last resort
def _parse_cors_from_env() -> List[str]:
    origins: List[str] = []
    env_origins = os.getenv("BACKEND_CORS_ORIGINS")
    if env_origins:
        for o in env_origins.split(","):
            o = o.strip()
            if o:
                origins.append(o)
    else:
        frontend = os.getenv("REACT_APP_FRONTEND_URL")
        if frontend:
            origins.append(frontend.strip())
        else:
            # defaults: permissive in dev
            origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "*",
            ]
    return origins


# Apply CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_from_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Healthcheck path configurable by env (default /api/health per task requirement)
HEALTHCHECK_PATH = os.getenv("HEALTHCHECK_PATH", "/api/health")


# PUBLIC_INTERFACE
@app.get(
    HEALTHCHECK_PATH,
    tags=["Utility"],
    summary="Health Check",
    description="Simple health endpoint to verify the API is running. Returns JSON { 'status': 'ok' } when healthy.",
)
def health_check():
    """
    Health check endpoint returning a simple status message.

    Returns:
        JSON object with a status indicator. Used by deployment readiness/liveness probes.
    """
    return {"status": "ok"}


# Register routers after app creation so routes are available for OpenAPI
# Legacy router (kept; not conflicting with new endpoints)
app.include_router(game_router)
# New deterministic endpoints for the game
app.include_router(seeded_router)
