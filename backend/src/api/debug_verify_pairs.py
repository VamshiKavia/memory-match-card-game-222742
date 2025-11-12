from __future__ import annotations

from collections import Counter

from src.api.game_service import _generate_deck  # type: ignore
from src.api.models import BoardSize


def verify_pairs_for_size(size: BoardSize) -> None:
    """Utility to verify that generated deck contains exactly N/2 values each duplicated twice."""
    deck = _generate_deck(size)
    total = len(deck)
    expected_pairs = total // 2
    counts = Counter(deck)
    distinct = len(counts)
    problems = []

    if distinct != expected_pairs:
        problems.append(f"Expected {expected_pairs} distinct values, got {distinct}")

    bad_multiplicities = {v: c for v, c in counts.items() if c != 2}
    if bad_multiplicities:
        problems.append(f"Values not duplicated exactly twice: {bad_multiplicities}")

    if problems:
        print(f"[FAIL] Deck verification failed for size {size}:")
        for p in problems:
            print(f"  - {p}")
    else:
        print(f"[OK] Deck verification passed for size {size}: "
              f"{expected_pairs} pairs, total {total} cards.")


if __name__ == "__main__":
    # Simple console checks. Run:
    #   python -m src.api.debug_verify_pairs
    verify_pairs_for_size(BoardSize.SMALL_4x4)
    verify_pairs_for_size(BoardSize.LARGE_6x6)
