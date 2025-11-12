from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.game_routes import router as game_router

openapi_tags = [
    {
        "name": "Game",
        "description": "Memory Flip Card game endpoints.",
    },
    {
        "name": "Utility",
        "description": "Utility and health endpoints.",
    },
]

app = FastAPI(
    title="Memory Flip Card Game API",
    description="Backend API for a Memory Flip Card game with in-memory session management.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Keep permissive CORS for frontend integration; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via env in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["Utility"],
    summary="Health Check",
    description="Simple health endpoint to verify the API is running.",
)
def health_check():
    """Health check endpoint returning a simple status message."""
    return {"message": "Healthy"}


# Register game API router under /api
app.include_router(game_router)
