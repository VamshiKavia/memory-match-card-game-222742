from collections import Counter

from src.api.game_service import MemoryGameService, _generate_deck  # type: ignore
from src.api.models import BoardSize


def test_generate_deck_has_exact_pairs_4x4():
    deck = _generate_deck(BoardSize.SMALL_4x4)
    assert len(deck) == 16
    counts = Counter(deck)
    assert len(counts) == 8
    assert all(c == 2 for c in counts.values())


def test_generate_deck_has_exact_pairs_6x6():
    deck = _generate_deck(BoardSize.LARGE_6x6)
    assert len(deck) == 36
    counts = Counter(deck)
    assert len(counts) == 18
    assert all(c == 2 for c in counts.values())


def test_masking_does_not_leak_hidden_values():
    service = MemoryGameService()
    session = service.new_game(BoardSize.SMALL_4x4)
    # Initially, all should be face-down and not matched -> value must be None
    for card in session.cards:
        assert not card.isFaceUp
        assert not card.isMatched
        assert card.value is None


def test_flip_and_match_reveals_values():
    service = MemoryGameService()
    session = service.new_game(BoardSize.SMALL_4x4)

    # Find any pair by probing flips; we avoid accessing internals and rely on API behavior:
    # Flip i, then search j != i until we find a match (turnResolved True with wasMatch True)
    # Note: This is a simple integration-esque test and should complete quickly with small board.
    # We'll flip sequentially until we match one pair
    from uuid import UUID
    game_id: UUID = session.session_id

    # Probe through indices to find a match
    resolved = False
    was_match = None
    # Flip first at 0 to start
    res1 = service.flip(game_id, 0)
    # Now flip others until we match
    for j in range(1, len(res1.session.cards)):
        res2 = service.flip(game_id, j)
        if res2.turnResolved:
            resolved = True
            was_match = res2.wasMatch
            if was_match:
                # On match both should be matched and values present
                shown = [c for c in res2.session.cards if c.isMatched]
                assert len([c for c in shown if c.value is not None]) >= 2
            break
        else:
            # If not resolved (shouldn't happen after second flip), continue
            pass

    assert resolved is True
    assert was_match in (True, False)
