from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.api.seeded_service import (
    Difficulty,
    GameId,
    SeededGameService,
    determine_difficulty,
)

router = APIRouter(prefix="/api", tags=["Game"])


# PUBLIC_INTERFACE
class CreateGameRequest(BaseModel):
    """Body for creating a new seeded game session."""
    difficulty: Optional[Difficulty] = Field(
        default=None, description="Difficulty level. Defaults to 'easy' if omitted."
    )
    seed: Optional[str] = Field(
        default=None,
        description="Optional seed string. If omitted, server generates a seed.",
    )


# PUBLIC_INTERFACE
class CreateGameResponse(BaseModel):
    """Response for new seeded game session."""
    gameId: GameId = Field(..., description="Server-generated game identifier.")
    seed: str = Field(..., description="Seed used for deterministic shuffling.")
    difficulty: Difficulty = Field(..., description="Selected difficulty for the deck.")


# PUBLIC_INTERFACE
class Card(BaseModel):
    """Card representation without leakage of matched state."""
    id: str = Field(..., description="Stable card ID for the session.")
    value: str = Field(..., description="Face value for rendering (pair identifier).")


# PUBLIC_INTERFACE
class MatchRequest(BaseModel):
    """Body for attempting a match with two card IDs."""
    firstId: str = Field(..., description="First card id to check for match.")
    secondId: str = Field(..., description="Second card id to check for match.")


# PUBLIC_INTERFACE
class MatchResponse(BaseModel):
    """Result of a match attempt."""
    isMatch: bool = Field(..., description="True if the two provided cards form a pair.")
    remainingPairs: int = Field(
        ..., description="Number of pairs remaining to be matched in this game."
    )


_service = SeededGameService()


# PUBLIC_INTERFACE
@router.get(
    "/health",
    tags=["Utility"],
    summary="API Health",
    description="Returns ok if the game API is healthy.",
)
def seeded_health() -> dict:
    """Additional health under /api/health (also provided at app level)."""
    return {"status": "ok"}


# PUBLIC_INTERFACE
@router.post(
    "/game",
    response_model=CreateGameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create seeded game",
    description="Create a new game with a deterministic deck derived from the seed.",
)
def create_game(payload: CreateGameRequest = Body(default=CreateGameRequest())) -> CreateGameResponse:
    """Create a new seeded game session and return identifiers."""
    difficulty = determine_difficulty(payload.difficulty)
    game = _service.create_game(difficulty=difficulty, seed=payload.seed)
    return CreateGameResponse(gameId=game.game_id, seed=game.seed, difficulty=game.difficulty)


# PUBLIC_INTERFACE
@router.get(
    "/game/{gameId}/deck",
    response_model=List[Card],
    summary="Get game deck",
    description="Returns deterministic shuffled list of cards excluding matched state.",
)
def get_deck(gameId: UUID = Path(..., description="Game session ID")) -> List[Card]:
    """Return current deck view (ids and face values only)."""
    deck = _service.get_deck(gameId)
    if deck is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Game not found"})
    return [Card(id=c.id, value=c.value) for c in deck]


# PUBLIC_INTERFACE
@router.post(
    "/game/{gameId}/match",
    response_model=MatchResponse,
    summary="Attempt match",
    description="Check whether the provided two card IDs form a pair.",
)
def post_match(
    gameId: UUID = Path(..., description="Game session ID"),
    payload: MatchRequest = Body(...),
) -> MatchResponse:
    """Attempt a match with two card ids for a game session."""
    try:
        is_match, remaining = _service.match(gameId, payload.firstId, payload.secondId)
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Game not found"})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={"code": "INVALID", "message": str(ve)})
    return MatchResponse(isMatch=is_match, remainingPairs=remaining)
