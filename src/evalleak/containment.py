"""Substring containment detection.

Exact and near duplicate checks compare whole records. They miss the case where
a short evaluation item is embedded inside a longer training record: a question
that appears verbatim as one paragraph of a longer document, for example. The
evaluation item is fully present in the training data, so the model may have
seen the answer, yet neither the digest nor the Jaccard of the whole records
matches.

This module detects that. For an ordered pair (short, long) it reports
containment when the normalised short text is a substring of the normalised
long text. It classifies the position as prefix, suffix, or interior so a
reader can judge how the item sits inside the record.

Very short items are noise: a two-word evaluation record is contained in almost
any document by chance. min_length guards against that, measured on the
normalised short text.
"""

from __future__ import annotations

from dataclasses import dataclass

from .normalise import NormaliseConfig, normalise


@dataclass(frozen=True)
class Containment:
    """A containment finding: short_id sits inside long_id."""

    short_id: str
    long_id: str
    position: str  # "prefix", "suffix", or "interior"


def _position(haystack: str, needle: str) -> str:
    if haystack.startswith(needle):
        return "prefix"
    if haystack.endswith(needle):
        return "suffix"
    return "interior"


def find_containment(
    short_text: str,
    long_text: str,
    *,
    config: NormaliseConfig = NormaliseConfig(),
    min_length: int = 16,
) -> str | None:
    """Return the containment position if short is inside long, else None.

    Both texts are normalised with the same config first. A short text whose
    normalised form is below min_length characters is ignored to avoid trivial
    coincidental matches.
