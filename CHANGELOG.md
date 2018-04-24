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
- Pairwise split comparison with directional contamination rates and intra-split
  duplicate detection (overlap.py).
- Line-oriented report rendering (report.py).
- CLI subcommands: exact, near, report, version.
- Exit codes: 0 clean, 1 contamination present, 2 usage error.
- Sample fixtures for one exact, one near, one containment, and one intra-split
