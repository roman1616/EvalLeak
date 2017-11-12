"""Command line interface for evalleak.

Subcommands:

    exact    load split manifests and print exact cross-split duplicates
    near     load split manifests and print near duplicates by Jaccard estimate
    report   load split manifests and print the full contamination report
    version  print the package version

Exit codes: 0 clean, 1 contamination present, 2 usage error. argparse itself
exits with 2 on argument errors, which matches the standard.
"""

from __future__ import annotations

import argparse
