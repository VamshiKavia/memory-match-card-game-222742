from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.api.game_service import MemoryGameService
from src.api.models import (
    BoardSize,
    FlipResult,
    GameSessionView,
    NewGameRequest,
)

# Router for all game endpoints
router = APIRouter(
    prefix="/api",
    tags=["Game"],
)


class ErrorResponse(BaseModel):
    """Standard error response schema for API errors."""
    code: str = Field(..., description="Stable error code identifier.")
    message: str = Field(..., description="Human-readable error message.")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error context if available."
    )


# PUBLIC_INTERFACE
@router.post(
    "/game",
    response_model=GameSessionView,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new game session",
    description="Initialize a new Memory Flip Card game session for the selected board size.",
    responses={
        201: {"description": "Game session created successfully."},
        422: {"description": "Validation error."},
        500: {"description": "Internal server error.", "model": ErrorResponse},
    },
)
def create_game(payload: NewGameRequest = Body(...)) -> GameSessionView:
    """Create a new game session and return its initial state."""
    try:
        service = MemoryGameService()
        return service.new_game(payload.size)
    except Exception as exc:
        # Unexpected error path
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(code="INTERNAL_ERROR", message=str(exc)).model_dump(),
        )


# PUBLIC_INTERFACE
@router.get(
    "/game/{gameId}",
    response_model=GameSessionView,
    summary="Get game state",
    description="Retrieve the current state of a game session by its ID.",
    responses={
        200: {"description": "Current game state returned."},
        404: {"description": "Game not found or expired.", "model": ErrorResponse},
        422: {"description": "Validation error."},
    },
)
def get_game(
    gameId: UUID = Path(..., description="Unique identifier of the game session."),
) -> GameSessionView:
    """Fetch current game session state. Returns 404 if not found or expired."""
    service = MemoryGameService()
    view = service.get_game(gameId)
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="NOT_FOUND", message="Game session not found or expired."
            ).model_dump(),
        )
    return view


class FlipRequest(BaseModel):
    """Request body for flipping a card."""
    index: int = Field(
        ..., ge=0, description="Zero-based index of the card to flip within the session."
    )


# PUBLIC_INTERFACE
@router.post(
    "/game/{gameId}/flip",
    response_model=FlipResult,
    summary="Flip a card",
    description=(
        "Flip a card at the provided index within the given game session. "
        "On a second flip, the move count increases and the turn is resolved."
    ),
    responses={
        200: {"description": "Flip result returned."},
        400: {"description": "Invalid flip (e.g., out-of-bounds).", "model": ErrorResponse},
        404: {"description": "Game not found or expired.", "model": ErrorResponse},
        422: {"description": "Validation error."},
    },
)
def flip_card(
    gameId: UUID = Path(..., description="Unique identifier of the game session."),
    payload: FlipRequest = Body(...),
) -> FlipResult:
    """Flip a card for a session and return the resulting state."""
    service = MemoryGameService()
    # First verify session existence to distinguish 404 vs 400
    existing = service.get_game(gameId)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="NOT_FOUND", message="Game session not found or expired."
            ).model_dump(),
        )
    try:
        result = service.flip(gameId, payload.index)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(code="INVALID_OPERATION", message=str(ve)).model_dump(),
        )


class ResetGameResponse(BaseModel):
    """Response indicating a reset has completed along with the fresh session view."""
    session: GameSessionView = Field(..., description="Newly initialized session view.")


# PUBLIC_INTERFACE
@router.post(
    "/game/{gameId}/reset",
    response_model=ResetGameResponse,
    summary="Reset game session",
    description=(
        "Reset an existing session to a fresh new game with the same board size. "
        "This creates a new internal session with a new deck but returns it under the same route."
    ),
    responses={
        200: {"description": "Game reset successfully."},
        404: {"description": "Game not found or expired.", "model": ErrorResponse},
    },
)
def reset_game(
    gameId: UUID = Path(..., description="Unique identifier of the game session."),
) -> ResetGameResponse:
    """
    Reset the game session by creating a new game with the same board size as the existing one.

    Note: This uses the existing session's size to create a fresh game. Since the
    MemoryGameService is in-memory, the new session will have different state and ID.
    """
    service = MemoryGameService()
    # Retrieve existing to discover the size
    existing = service.get_game(gameId)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="NOT_FOUND", message="Game session not found or expired."
            ).model_dump(),
        )
    # Initialize a new game with same size
    fresh = service.new_game(BoardSize(existing.size))
    return ResetGameResponse(session=fresh)
