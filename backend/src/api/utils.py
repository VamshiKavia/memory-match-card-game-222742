from __future__ import annotations

import hashlib
import random
from typing import List


# PUBLIC_INTERFACE
def deterministic_shuffle(items: List[str], seed: str) -> List[str]:
    """Return a deterministically shuffled copy of the items using a string seed.

    Uses SHA-256 of the seed to construct a numeric seed for random.Random to ensure
    cross-platform stable order.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rnd = random.Random(int(digest, 16))
    arr = list(items)
    rnd.shuffle(arr)
    return arr
