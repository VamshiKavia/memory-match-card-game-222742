from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from src.api.models import (
    BoardSize,
    CardView,
    FlipResult,
    GameSessionView,
)


DEFAULT_SESSION_TTL_SECONDS = 120 * 60  # 120 minutes


@dataclass
class _GameSession:
    """Internal in-memory representation of a game session."""
    session_id: UUID
    size: BoardSize
    deck: List[int]  # length N; values from 0..(N/2-1), each appearing twice
    face_up: List[bool]  # length N
    matched: List[bool]  # length N
    first_selection: Optional[int]  # index or None
    move_count: int
    matched_pairs: int
    created_at: float
    updated_at: float

    @property
    def total_cards(self) -> int:
        return len(self.deck)

    @property
    def total_pairs(self) -> int:
        return len(self.deck) // 2

    @property
    def game_over(self) -> bool:
        return self.matched_pairs == self.total_pairs


def _generate_deck(size: BoardSize) -> List[int]:
    """Generate a shuffled deck of pair values for the given size."""
    total = BoardSize.to_card_count(size)
    pairs = total // 2
    base = [i for i in range(pairs) for _ in range(2)]
    random.shuffle(base)
    return base


def _now_ts() -> float:
    return time.time()


def _make_card_view(idx: int, session: _GameSession) -> CardView:
    is_face_up = session.face_up[idx]
    is_matched = session.matched[idx]
    value: Optional[int] = session.deck[idx] if (is_face_up or is_matched) else None
    return CardView(index=idx, isFaceUp=is_face_up, isMatched=is_matched, value=value)


def _make_session_view(session: _GameSession) -> GameSessionView:
    cards = [_make_card_view(i, session) for i in range(session.total_cards)]
    return GameSessionView(
        session_id=session.session_id,
        size=session.size,
        moveCount=session.move_count,
        gameOver=session.game_over,
        cards=cards,
        firstSelection=session.first_selection,
        matchedCount=session.matched_pairs,
        createdAt=session.created_at,
        updatedAt=session.updated_at,
    )


class _SessionStore:
    """Simple in-memory session store with TTL eviction on access."""

    def __init__(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: Dict[UUID, _GameSession] = {}

    def _evict_expired(self) -> None:
        if not self._sessions:
            return
        now = _now_ts()
        expired: List[UUID] = []
        for sid, sess in self._sessions.items():
            if (now - sess.updated_at) > self._ttl_seconds:
                expired.append(sid)
        for sid in expired:
            del self._sessions[sid]

    # PUBLIC_INTERFACE
    def create(self, size: BoardSize) -> _GameSession:
        """Create and store a new session for the requested board size."""
        self._evict_expired()
        session_id = uuid4()
        deck = _generate_deck(size)
        n = len(deck)
        ts = _now_ts()
        session = _GameSession(
            session_id=session_id,
            size=size,
            deck=deck,
            face_up=[False] * n,
            matched=[False] * n,
            first_selection=None,
            move_count=0,
            matched_pairs=0,
            created_at=ts,
            updated_at=ts,
        )
        self._sessions[session_id] = session
        return session

    # PUBLIC_INTERFACE
    def get(self, session_id: UUID) -> Optional[_GameSession]:
        """Retrieve a session by ID, performing TTL eviction before access."""
        self._evict_expired()
        return self._sessions.get(session_id)

    # PUBLIC_INTERFACE
    def put(self, session: _GameSession) -> None:
        """Update/replace a session, preserving same ID."""
        self._sessions[session.session_id] = session


class MemoryGameService:
    """Pure in-memory memory game service. Side-effect free except for internal store."""

    def __init__(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS) -> None:
        self._store = _SessionStore(ttl_seconds=ttl_seconds)

    # PUBLIC_INTERFACE
    def new_game(self, size: BoardSize) -> GameSessionView:
        """Create a new game and return its initial view state."""
        session = self._store.create(size)
        return _make_session_view(session)

    # PUBLIC_INTERFACE
    def get_game(self, session_id: UUID) -> Optional[GameSessionView]:
        """Get current game state for a session ID, or None if not found/expired."""
        session = self._store.get(session_id)
        if session is None:
            return None
        return _make_session_view(session)

    # PUBLIC_INTERFACE
    def flip(self, session_id: UUID, index: int) -> FlipResult:
        """Flip a card within a session and return result state.

        Rules:
        - First flip: reveal card; do not increment move count.
        - Second flip: reveal card; increment move count by 1 and check for match.
          - If values match: mark both as matched; they remain face-up.
          - If not a match: both are temporarily face-up in the response; state clears
            first selection and turns both cards face-down for subsequent actions.

        Edge cases:
        - Ignore flips on already matched cards.
        - Ignore flipping the same index as an already face-up first selection.
        - Index must be within range; otherwise raise ValueError.
        """
        session = self._store.get(session_id)
        if session is None:
            raise ValueError("Session not found or expired")

        if index < 0 or index >= session.total_cards:
            raise ValueError("Flip index out of bounds")

        # If the game is already over, just return the view as-is
        if session.game_over:
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=_make_session_view(session), turnResolved=False, wasMatch=None)

        # Ignore flips on already matched cards
        if session.matched[index]:
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=_make_session_view(session), turnResolved=False, wasMatch=None)

        # First selection
        if session.first_selection is None:
            # If the card is already face-up (possible from previous turn non-match UI),
            # but not matched, treat it as first selection if it's not currently marked.
            if not session.face_up[index]:
                session.face_up[index] = True
            session.first_selection = index
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=_make_session_view(session), turnResolved=False, wasMatch=None)

        # Second selection
        if index == session.first_selection:
            # Flipping the same card again does nothing.
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=_make_session_view(session), turnResolved=False, wasMatch=None)

        second_index = index
        # Reveal second card
        if not session.face_up[second_index]:
            session.face_up[second_index] = True

        first_index = session.first_selection
        was_match = session.deck[first_index] == session.deck[second_index]

        # Increment move count on second flip
        session.move_count += 1

        if was_match:
            # Mark both as matched; keep them face-up
            session.matched[first_index] = True
            session.matched[second_index] = True
            session.matched_pairs += 1
            session.first_selection = None
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=_make_session_view(session), turnResolved=True, wasMatch=True)

        else:
            # Not a match: for the returned view, both are face-up.
            # After returning state, we reset them to face-down for next actions.
            # To achieve this without external side-effects, we:
            # - Build current view snapshot,
            # - Then mutate internal state back (face_down) and clear first_selection.
            snapshot_session = _clone_session(session)
            snapshot_session.face_up[first_index] = True
            snapshot_session.face_up[second_index] = True

            # Build response first
            response_view = _make_session_view(snapshot_session)

            # Reset for subsequent actions
            session.face_up[first_index] = False
            session.face_up[second_index] = False
            session.first_selection = None
            session.updated_at = _now_ts()
            self._store.put(session)
            return FlipResult(session=response_view, turnResolved=True, wasMatch=False)


def _clone_session(s: _GameSession) -> _GameSession:
    """Create a shallow clone of session for snapshotting response views."""
    return _GameSession(
        session_id=s.session_id,
        size=s.size,
        deck=list(s.deck),
        face_up=list(s.face_up),
        matched=list(s.matched),
        first_selection=s.first_selection,
        move_count=s.move_count,
        matched_pairs=s.matched_pairs,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )
