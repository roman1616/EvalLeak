"""Text normalisation with each step individually switchable.

Normalisation decides which records count as "the same". A more aggressive
setting collapses more surface differences and therefore reports more
contamination. Making each step a separate flag keeps that trade off visible:
you can see exactly which transformation caused two records to match.

Steps, applied in this fixed order when enabled:

1. whitespace: collapse every run of whitespace to a single space and strip
   the ends. Line breaks and tabs become spaces.
2. case: lowercase the text.
3. punctuation: drop the ASCII punctuation characters, then re-collapse
   whitespace so removed punctuation does not leave double spaces.

The order matters. Case folding before punctuation removal does not change the
result here, but whitespace collapse runs first so later steps see a single
canonical spacing.
"""

from __future__ import annotations

import hashlib
import string
from dataclasses import dataclass

_PUNCTUATION = set(string.punctuation)


@dataclass(frozen=True)
class NormaliseConfig:
    """Which normalisation steps are enabled.

    The default enables all three, the most aggressive setting, because that is
    the safest default for contamination detection: it is better to flag a
    borderline match for a human to dismiss than to miss a real leak.
    """

    whitespace: bool = True
    case: bool = True
    punctuation: bool = True

    def describe(self) -> str:
        """Return a stable one-line description of the active steps."""
        parts = [
            ("whitespace", self.whitespace),
            ("case", self.case),
            ("punctuation", self.punctuation),
        ]
        active = [name for name, on in parts if on]
        return ",".join(active) if active else "none"


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _drop_punctuation(text: str) -> str:
    out = []
    for ch in text:
        if ch in _PUNCTUATION:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


