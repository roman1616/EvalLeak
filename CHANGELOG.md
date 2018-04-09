# Changelog

All notable changes to this project are recorded here.

## 0.1.0 - 2026-09-02

Initial release.

- Split manifest parser with loud failure on malformed input (records.py).
- Normalisation with individually switchable whitespace, case, and punctuation
  steps (normalise.py).
- Character k-shingling and a hashlib MinHash sketch for a Jaccard estimate
  (shingle.py).
- Prefix, suffix, and interior substring containment detection (containment.py).
