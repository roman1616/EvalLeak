"""Character k-shingles and a MinHash sketch for a Jaccard estimate.

Two records rarely match byte for byte after an edit, so exact digest matching
misses near duplicates. Character k-shingling turns each record into the set of
its length-k substrings, and the Jaccard similarity of two such sets measures
how much text they share regardless of small edits.

Computing exact Jaccard needs both full sets in memory and a set intersection
per pair, which is quadratic in the number of records. A MinHash sketch trades
a small, bounded error for a fixed-size signature: the fraction of matching
minima across the signatures estimates the true Jaccard. The sketch here is
built only on hashlib, so it is deterministic and depends on no third-party
library.

Determinism: the num_perm hash "permutations" are simulated by salting sha256
with the permutation index. The same input always yields the same signature.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_MAX_HASH = (1 << 64) - 1


def shingles(text: str, k: int = 5) -> set[str]:
    """Return the set of character k-shingles of text.

    If the text is shorter than k, the whole text is returned as one shingle so
    short records still compare sensibly.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if len(text) <= k:
        return {text} if text else set()
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def _hash_shingle(shingle: str, perm: int) -> int:
    """Hash one shingle under permutation index perm to a 64-bit integer."""
    payload = f"{perm}\x00{shingle}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True)
