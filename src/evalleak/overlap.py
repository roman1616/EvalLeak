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
    num_perm: int
    near_threshold: float
    min_containment: int
    counts: dict[str, int] = field(default_factory=dict)
    exact: list[ExactMatch] = field(default_factory=list)
    near: list[NearMatch] = field(default_factory=list)
    containment: list[ContainmentMatch] = field(default_factory=list)
    intra: list[IntraDuplicate] = field(default_factory=list)
    pair_rates: list[PairRate] = field(default_factory=list)

    def contaminated_ids(self) -> dict[str, set[str]]:
        """Map each split to the set of its record ids involved in any finding."""
        out: dict[str, set[str]] = {split: set() for split in self.counts}
        for m in self.exact:
            out.setdefault(m.split_a, set()).add(m.id_a)
            out.setdefault(m.split_b, set()).add(m.id_b)
        for m in self.near:
            out.setdefault(m.split_a, set()).add(m.id_a)
            out.setdefault(m.split_b, set()).add(m.id_b)
        for m in self.containment:
            out.setdefault(m.split_short, set()).add(m.id_short)
            out.setdefault(m.split_long, set()).add(m.id_long)
        for m in self.intra:
            out.setdefault(m.split, set()).add(m.id_a)
            out.setdefault(m.split, set()).add(m.id_b)
        return out

    def total_contaminated(self) -> int:
        """Return the total distinct contaminated records across all splits."""
        return sum(len(ids) for ids in self.contaminated_ids().values())

    def has_findings(self) -> bool:
        return bool(self.exact or self.near or self.containment or self.intra)


def _digests(manifest: Manifest, config: NormaliseConfig) -> dict[str, str]:
    return {r.record_id: digest(r.text, config) for r in manifest.records}


def _minhashes(
    manifest: Manifest, config: NormaliseConfig, k: int, num_perm: int
) -> dict[str, MinHash]:
    from .normalise import normalise

    out: dict[str, MinHash] = {}
    for r in manifest.records:
        norm = normalise(r.text, config)
        out[r.record_id] = MinHash.from_shingles(shingles(norm, k), num_perm)
    return out


def compare(
    manifests: list[Manifest],
    *,
    config: NormaliseConfig = NormaliseConfig(),
    k: int = 5,
    num_perm: int = 128,
    near_threshold: float = 0.6,
    min_containment: int = 16,
) -> OverlapReport:
    """Run all detectors across the given manifests and build a report.

    Manifests are processed in the order given, and split pairs are compared in
    sorted split-name order so output is deterministic.
    """
    report = OverlapReport(
        config=config,
        k=k,
        num_perm=num_perm,
        near_threshold=near_threshold,
        min_containment=min_containment,
        counts={m.split: len(m) for m in manifests},
    )

    by_split = {m.split: m for m in manifests}
    digests = {name: _digests(m, config) for name, m in by_split.items()}
    minhashes = {
        name: _minhashes(m, config, k, num_perm) for name, m in by_split.items()
    }
    texts = {
        name: {r.record_id: r.text for r in m.records} for name, m in by_split.items()
    }

    split_names = sorted(by_split)

    # Intra-split exact duplication.
    for name in split_names:
        records = by_split[name].records
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                if digests[name][records[i].record_id] == digests[name][
                    records[j].record_id
                ]:
                    report.intra.append(
                        IntraDuplicate(
                            split=name,
                            id_a=records[i].record_id,
                            id_b=records[j].record_id,
                            digest=digests[name][records[i].record_id],
                        )
                    )

    # Cross-split comparisons over unordered pairs of splits.
    for ai in range(len(split_names)):
        for bi in range(ai + 1, len(split_names)):
            name_a = split_names[ai]
            name_b = split_names[bi]
            recs_a = by_split[name_a].records
            recs_b = by_split[name_b].records

            exact_pairs: set[tuple[str, str]] = set()
            for ra in recs_a:
                for rb in recs_b:
                    da = digests[name_a][ra.record_id]
                    db = digests[name_b][rb.record_id]
                    if da == db:
                        report.exact.append(
                            ExactMatch(
                                split_a=name_a,
                                id_a=ra.record_id,
                                split_b=name_b,
                                id_b=rb.record_id,
                                digest=da,
                            )
                        )
                        exact_pairs.add((ra.record_id, rb.record_id))

            for ra in recs_a:
                for rb in recs_b:
                    if (ra.record_id, rb.record_id) in exact_pairs:
                        continue
                    est = minhashes[name_a][ra.record_id].jaccard(
                        minhashes[name_b][rb.record_id]
                    )
                    if est >= near_threshold:
                        report.near.append(
                            NearMatch(
                                split_a=name_a,
                                id_a=ra.record_id,
                                split_b=name_b,
                                id_b=rb.record_id,
                                jaccard=est,
                            )
                        )

            # Containment in both directions across the pair.
            for ra in recs_a:
                for rb in recs_b:
                    if (ra.record_id, rb.record_id) in exact_pairs:
                        continue
                    ta = texts[name_a][ra.record_id]
                    tb = texts[name_b][rb.record_id]
                    if len(ta) <= len(tb):
                        pos = find_containment(
                            ta, tb, config=config, min_length=min_containment
                        )
                        if pos is not None:
                            report.containment.append(
                                ContainmentMatch(
                                    split_short=name_a,
                                    id_short=ra.record_id,
                                    split_long=name_b,
                                    id_long=rb.record_id,
                                    position=pos,
                                )
                            )
                    else:
                        pos = find_containment(
                            tb, ta, config=config, min_length=min_containment
                        )
                        if pos is not None:
                            report.containment.append(
                                ContainmentMatch(
                                    split_short=name_b,
                                    id_short=rb.record_id,
                                    split_long=name_a,
                                    id_long=ra.record_id,
                                    position=pos,
                                )
                            )

    _sort_findings(report)
    report.pair_rates = _compute_pair_rates(report, by_split, split_names)
    return report


def _sort_findings(report: OverlapReport) -> None:
    report.exact.sort(key=lambda m: (m.split_a, m.id_a, m.split_b, m.id_b))
    report.near.sort(key=lambda m: (m.split_a, m.id_a, m.split_b, m.id_b))
    report.containment.sort(
        key=lambda m: (m.split_short, m.id_short, m.split_long, m.id_long)
    )
    report.intra.sort(key=lambda m: (m.split, m.id_a, m.id_b))


def _compute_pair_rates(
    report: OverlapReport,
    by_split: dict[str, Manifest],
    split_names: list[str],
) -> list[PairRate]:
    """Compute directional contamination rates for every ordered split pair."""
    # Collect, per ordered pair, the target ids touched by any cross finding.
    touched: dict[tuple[str, str], set[str]] = {}

    def touch(source: str, target: str, target_id: str) -> None:
        touched.setdefault((source, target), set()).add(target_id)

    for m in report.exact:
        touch(m.split_a, m.split_b, m.id_b)
        touch(m.split_b, m.split_a, m.id_a)
    for m in report.near:
        touch(m.split_a, m.split_b, m.id_b)
        touch(m.split_b, m.split_a, m.id_a)
    for m in report.containment:
        touch(m.split_long, m.split_short, m.id_short)
        touch(m.split_short, m.split_long, m.id_long)

    rates: list[PairRate] = []
    for source in split_names:
        for target in split_names:
            if source == target:
                continue
            contaminated = len(touched.get((source, target), set()))
            if contaminated == 0:
                continue
            rates.append(
                PairRate(
                    source=source,
                    target=target,
                    contaminated=contaminated,
                    total=len(by_split[target]),
                )
            )
    rates.sort(key=lambda r: (r.source, r.target))
# review note
