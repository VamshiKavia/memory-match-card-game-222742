from __future__ import annotations

import hashlib
import random
import string
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4


# PUBLIC_INTERFACE
class Difficulty(str, Enum):
    """Difficulty enumeration for the seeded deck service."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# PUBLIC_INTERFACE
def determine_difficulty(value: Optional["Difficulty"]) -> "Difficulty":
    """Resolve difficulty with default.

    Prefer Enum values; fallback to parsing strings case-insensitively.
    """
    if isinstance(value, Difficulty):
        return value
    # Accept string inputs defensively
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {Difficulty.EASY.value, Difficulty.MEDIUM.value, Difficulty.HARD.value}:
            return Difficulty(v)
    # default
    return Difficulty.EASY


# PUBLIC_INTERFACE
class GameId(UUID):
    """Type alias for game IDs."""


@dataclass
class _Card:
    id: str
    value: str  # face value used by client to render


@dataclass
class _Game:
    game_id: UUID
    seed: str
    difficulty: Difficulty
    deck: List[_Card]
    matched_ids: Dict[str, bool]
    total_pairs: int
    created_at: float
    updated_at: float
    # Track total moves (each match attempt increments once)
    move_count: int
    # Cached completion flag for quick checks
    completed: bool


class _SeedRandom:
    """Small wrapper around random.Random seeded from a stable hash of a string."""
    def __init__(self, seed: str) -> None:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        # Use int seed from hex digest for stability
        self._rnd = random.Random(int(digest, 16))

    # PUBLIC_INTERFACE
    def shuffle(self, items: List[str]) -> List[str]:
        """Return a new list shuffled deterministically."""
        arr = list(items)
        self._rnd.shuffle(arr)
        return arr

    # PUBLIC_INTERFACE
    def choice(self, seq):
        return self._rnd.choice(seq)

    # PUBLIC_INTERFACE
    def randint(self, a: int, b: int) -> int:
        return self._rnd.randint(a, b)


def _now() -> float:
    return time.time()


def _pair_values_for_difficulty(diff: Difficulty) -> List[str]:
    """Return the set of face values to use for a given difficulty (before pairing/shuffle)."""
    # Keep values as simple strings (e.g., uppercase letters, numbers, or emoji).
    # For determinism, the source list order must be stable.
    easy = ["A", "B", "C", "D", "E", "F", "G", "H"]             # 8 pairs (16 cards)
    medium = [c for c in string.ascii_uppercase[:12]]            # 12 pairs (24 cards)
    hard = [c for c in string.ascii_uppercase[:18]]              # 18 pairs (36 cards)

    if diff == Difficulty.EASY:
        values = easy
    elif diff == Difficulty.MEDIUM:
        values = medium
    else:
        values = hard
    return values


def _build_deck(seed: str, diff: Difficulty) -> List[_Card]:
    """Create a deterministic deck of cards (ids+values) based on seed and difficulty."""
    values = _pair_values_for_difficulty(diff)
    # Duplicate each value to form pairs
    faces: List[str] = [v for v in values for _ in (0, 1)]
    rnd = _SeedRandom(seed)
    shuffled_faces = rnd.shuffle(faces)

    # Create stable ids per position derived from seed + index
    deck: List[_Card] = []
    for idx, face in enumerate(shuffled_faces):
        stable_id = hashlib.sha1(f"{seed}:{idx}".encode("utf-8")).hexdigest()[:16]
        deck.append(_Card(id=stable_id, value=face))
    return deck


class SeededGameService:
    """In-memory deterministic game session manager based on seed and difficulty."""

    def __init__(self) -> None:
        self._games: Dict[UUID, _Game] = {}

    # PUBLIC_INTERFACE
    def create_game(self, difficulty: Difficulty, seed: Optional[str]) -> _Game:
        """Create game using provided or generated seed."""
        use_seed = seed or self._generate_seed()
        deck = _build_deck(use_seed, difficulty)
        total_pairs = len(deck) // 2
        now = _now()
        game = _Game(
            game_id=uuid4(),
            seed=use_seed,
            difficulty=difficulty,
            deck=deck,
            matched_ids={},
            total_pairs=total_pairs,
            created_at=now,
            updated_at=now,
            move_count=0,
            completed=False,
        )
        self._games[game.game_id] = game
        return game

    # PUBLIC_INTERFACE
    def get_deck(self, game_id: UUID) -> Optional[List[_Card]]:
        """Return deck if game exists."""
        game = self._games.get(game_id)
        if not game:
            return None
        # Masking: Only return id and value (no matched flags here) as the API layer handles exposure.
        return list(game.deck)

    # PUBLIC_INTERFACE
    def match(self, game_id: UUID, first_id: str, second_id: str) -> Tuple[bool, int, bool, int]:
        """Attempt to match two card ids.

        Returns:
            (is_match, remaining_pairs, is_completed, move_count)

        Raises:
            KeyError: if game not found
            ValueError: if ids invalid, identical, or already matched
        """
        game = self._games.get(game_id)
        if not game:
            raise KeyError("game not found")

        if first_id == second_id:
            raise ValueError("Cannot match a card with itself")

        # Lookup cards
        first = next((c for c in game.deck if c.id == first_id), None)
        second = next((c for c in game.deck if c.id == second_id), None)
        if not first or not second:
            raise ValueError("Unknown card id(s)")

        if game.matched_ids.get(first.id) or game.matched_ids.get(second.id):
            raise ValueError("One or both cards already matched")

        # Increment move count for every match attempt
        game.move_count += 1

        is_match = first.value == second.value
        if is_match:
            game.matched_ids[first.id] = True
            game.matched_ids[second.id] = True

        remaining = game.total_pairs - (len(game.matched_ids) // 2)
        game.completed = remaining == 0
        game.updated_at = _now()
        self._games[game_id] = game
        return is_match, remaining, game.completed, game.move_count

    # PUBLIC_INTERFACE
    def get_stats(self, game_id: UUID) -> Optional[Tuple[int, bool]]:
        """Return (move_count, completed) if game exists, else None."""
        game = self._games.get(game_id)
        if not game:
            return None
        return game.move_count, game.completed

    def _generate_seed(self) -> str:
        """Generate user-friendly random seed string."""
        # 12-char alphanum seed
        alphabet = string.ascii_letters + string.digits
        rnd = random.SystemRandom()
        return "".join(rnd.choice(alphabet) for _ in range(12))
