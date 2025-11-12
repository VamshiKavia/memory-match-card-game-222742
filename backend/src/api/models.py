from __future__ import annotations

from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BoardSize(str, Enum):
    """Enumeration of supported board sizes for the memory game."""
    SMALL_4x4 = "4x4"
    LARGE_6x6 = "6x6"

    # PUBLIC_INTERFACE
    @staticmethod
    def to_card_count(size: "BoardSize") -> int:
        """Return total number of cards for a given board size."""
        if size == BoardSize.SMALL_4x4:
            return 16
        if size == BoardSize.LARGE_6x6:
            return 36
        raise ValueError(f"Unsupported board size: {size}")


# PUBLIC_INTERFACE
class NewGameRequest(BaseModel):
    """Request payload to create a new memory game session."""
    size: BoardSize = Field(
        default=BoardSize.SMALL_4x4,
        description="Board size to initialize (4x4=16 cards, 6x6=36 cards).",
    )

    @field_validator("size", mode="before")
    @classmethod
    def coerce_size(cls, v):
        """Coerce common string aliases into supported BoardSize values."""
        if isinstance(v, str):
            v = v.lower().strip()
            if v in {"4x4", "small", "16"}:
                return BoardSize.SMALL_4x4
            if v in {"6x6", "large", "36"}:
                return BoardSize.LARGE_6x6
        return v


# PUBLIC_INTERFACE
class FlipCardRequest(BaseModel):
    """Request payload to flip a card at a given index within a session."""
    session_id: UUID = Field(..., description="Unique identifier of the game session.")
    index: int = Field(..., ge=0, description="Zero-based index of the card to flip.")


# PUBLIC_INTERFACE
class CardView(BaseModel):
    """Readonly view representation of a single card for clients."""
    index: int = Field(..., description="Card's index within the deck.")
    isFaceUp: bool = Field(..., description="Whether the card is currently face-up.")
    isMatched: bool = Field(..., description="Whether the card is already matched.")
    # value is intentionally not exposed unless face-up or matched for fairness
    value: Optional[int] = Field(
        default=None,
        description="Card's value (pair identifier). Present only when face-up or already matched.",
    )


# PUBLIC_INTERFACE
class GameSessionView(BaseModel):
    """Client-facing representation of the game session state."""
    session_id: UUID = Field(..., description="Unique identifier for the session.")
    size: BoardSize = Field(..., description="Board size of the session.")
    moveCount: int = Field(..., ge=0, description="Total number of moves made so far.")
    gameOver: bool = Field(..., description="Whether all pairs have been matched.")
    cards: List[CardView] = Field(
        ..., description="List of cards with visibility dependent on state."
    )
    firstSelection: Optional[int] = Field(
        default=None, description="Index of the first selected card in an in-progress turn."
    )
    matchedCount: int = Field(
        ..., ge=0, description="Number of matched pairs so far."
    )
    updatedAt: float = Field(
        ..., description="Unix timestamp (seconds) when session was last updated."
    )
    createdAt: float = Field(
        ..., description="Unix timestamp (seconds) when session was created."
    )


# PUBLIC_INTERFACE
class FlipResult(BaseModel):
    """Result of a flip operation."""
    session: GameSessionView = Field(..., description="Updated session state.")
    turnResolved: bool = Field(
        ..., description="True if a pair was completed (second flip applied)."
    )
    wasMatch: Optional[bool] = Field(
        default=None,
        description="If turnResolved is true, indicates whether the pair matched.",
    )
