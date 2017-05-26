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
