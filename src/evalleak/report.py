"""Line-oriented rendering of overlap findings.

Every renderer returns a list of strings, one per output line, so results diff
cleanly in git and are easy to test. No wall-clock time or randomness appears
in the output, so identical input produces byte-identical output.
"""

from __future__ import annotations

from .overlap import OverlapReport


def _rate_pct(value: float) -> str:
    """Format a rate as a fixed two-decimal percentage."""
    return f"{value * 100:.2f}%"


def render_exact(report: OverlapReport) -> list[str]:
    lines = ["exact cross-split duplicates:"]
    if not report.exact:
        lines.append("  none")
        return lines
    for m in report.exact:
        lines.append(
            f"  {m.split_a}/{m.id_a} == {m.split_b}/{m.id_b}  digest={m.digest[:12]}"
        )
    return lines


def render_near(report: OverlapReport) -> list[str]:
    lines = [
        f"near cross-split duplicates (jaccard >= {report.near_threshold:.2f}, "
        f"k={report.k}, num_perm={report.num_perm}):"
    ]
    if not report.near:
        lines.append("  none")
        return lines
    for m in report.near:
        lines.append(
            f"  {m.split_a}/{m.id_a} ~ {m.split_b}/{m.id_b}  jaccard~={m.jaccard:.3f}"
        )
    return lines


def render_containment(report: OverlapReport) -> list[str]:
    lines = [f"containment (min_length={report.min_containment}):"]
    if not report.containment:
        lines.append("  none")
        return lines
    for m in report.containment:
        lines.append(
            f"  {m.split_short}/{m.id_short} inside {m.split_long}/{m.id_long}"
            f"  position={m.position}"
        )
    return lines


def render_intra(report: OverlapReport) -> list[str]:
    lines = ["intra-split duplicates:"]
    if not report.intra:
        lines.append("  none")
        return lines
    for m in report.intra:
        lines.append(
            f"  {m.split}/{m.id_a} == {m.split}/{m.id_b}  digest={m.digest[:12]}"
        )
    return lines


def render_rates(report: OverlapReport) -> list[str]:
    lines = ["contamination rate per split pair (source -> target):"]
    if not report.pair_rates:
        lines.append("  none")
        return lines
    for r in report.pair_rates:
        lines.append(
            f"  {r.source} -> {r.target}: {r.contaminated}/{r.total} "
            f"= {_rate_pct(r.rate)}"
