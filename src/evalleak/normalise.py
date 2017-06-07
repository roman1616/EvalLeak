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
