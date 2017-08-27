"""Pairwise split comparison and contamination rates.

This module runs the three detectors across split pairs and inside single
splits, then aggregates the findings into rates. An aggregate rate alone is not
actionable, so every finding names the specific record ids involved.

Definitions used here:

- exact: two records in different splits share a normalised digest.
- near: two records in different splits have an estimated Jaccard at or above a
  threshold, and are not already an exact match.
- containment: the shorter record's normalised text is a substring of the
  longer record's normalised text, across splits.
- intra: two records inside the same split are exact duplicates by digest.

The contamination rate for an ordered split pair (A, B) is the number of
distinct records in B that are contaminated by any record in A, divided by the
number of records in B. Reporting it per direction matters: leaking a training
record into a small test split is far worse than the reverse, and a single
symmetric number would hide that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .containment import Containment, find_containment
from .normalise import NormaliseConfig, digest
from .records import Manifest, Record
from .shingle import MinHash, shingles


@dataclass(frozen=True)
class ExactMatch:
    split_a: str
    id_a: str
    split_b: str
    id_b: str
    digest: str


@dataclass(frozen=True)
class NearMatch:
    split_a: str
    id_a: str
    split_b: str
    id_b: str
    jaccard: float


@dataclass(frozen=True)
class ContainmentMatch:
    split_short: str
    id_short: str
    split_long: str
    id_long: str
    position: str


@dataclass(frozen=True)
class IntraDuplicate:
    split: str
    id_a: str
    id_b: str
    digest: str


@dataclass(frozen=True)
class PairRate:
    """Contamination rate for records of `target` explained by `source`."""

    source: str
    target: str
    contaminated: int
    total: int

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.contaminated / self.total


@dataclass
class OverlapReport:
    config: NormaliseConfig
    k: int
