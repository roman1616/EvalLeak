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
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="character shingle length (default 5)",
    )
    parser.add_argument(
        "--num-perm",
        type=int,
        default=128,
        help="MinHash permutation count (default 128)",
    )
    parser.add_argument(
        "--near-threshold",
        type=float,
        default=0.6,
        help="minimum Jaccard estimate for a near duplicate (default 0.6)",
    )
    parser.add_argument(
        "--min-containment",
        type=int,
        default=16,
        help="minimum normalised length for a containment match (default 16)",
    )


def _config_from_args(args: argparse.Namespace) -> NormaliseConfig:
    return NormaliseConfig(
        whitespace=not args.no_whitespace,
        case=not args.no_case,
        punctuation=not args.no_punctuation,
    )


def _load_all(args: argparse.Namespace):
    manifests = []
    for path in args.manifests:
        manifests.append(load_manifest(path))
    return manifests


def _run_compare(args: argparse.Namespace):
    manifests = _load_all(args)
    return compare(
        manifests,
        config=_config_from_args(args),
        k=args.k,
        num_perm=args.num_perm,
        near_threshold=args.near_threshold,
        min_containment=args.min_containment,
    )


def _cmd_exact(args: argparse.Namespace) -> int:
    result = _run_compare(args)
    for line in report_module.render_exact(result):
        print(line)
    return 1 if result.exact else 0


def _cmd_near(args: argparse.Namespace) -> int:
    result = _run_compare(args)
    for line in report_module.render_near(result):
        print(line)
    return 1 if result.near else 0


def _cmd_report(args: argparse.Namespace) -> int:
    result = _run_compare(args)
    for line in report_module.render_report(result):
        print(line)
    return 1 if result.has_findings() else 0


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"evalleak {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalleak",
        description="Detect contamination between training and evaluation splits.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_exact = sub.add_parser("exact", help="print exact cross-split duplicates")
    _add_common(p_exact)
    p_exact.set_defaults(func=_cmd_exact)

    p_near = sub.add_parser("near", help="print near duplicates by Jaccard estimate")
    _add_common(p_near)
    p_near.set_defaults(func=_cmd_near)

    p_report = sub.add_parser("report", help="print the full contamination report")
    _add_common(p_report)
    p_report.set_defaults(func=_cmd_report)

    p_version = sub.add_parser("version", help="print the version")
    p_version.set_defaults(func=_cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
