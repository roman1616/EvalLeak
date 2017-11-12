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
import sys

from . import __version__, report as report_module
from .normalise import NormaliseConfig
from .overlap import compare
from .records import ManifestError, load_manifest


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "manifests",
        nargs="+",
        help="split manifest files to compare",
    )
    parser.add_argument(
        "--no-whitespace",
        action="store_true",
        help="disable whitespace normalisation",
    )
    parser.add_argument(
        "--no-case",
        action="store_true",
        help="disable case folding",
    )
    parser.add_argument(
        "--no-punctuation",
        action="store_true",
        help="disable punctuation removal",
    )
