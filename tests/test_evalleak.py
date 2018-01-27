"""Tests for evalleak, stdlib unittest only."""

import os
import unittest

from evalleak import __version__
from evalleak.cli import main
from evalleak.containment import find_containment
from evalleak.normalise import NormaliseConfig, digest, normalise
from evalleak.overlap import compare
from evalleak.records import ManifestError, parse_manifest
from evalleak.report import render_report
from evalleak.shingle import MinHash, exact_jaccard, shingles

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _sample(name):
    return os.path.join(SAMPLES, name)


class RecordsTests(unittest.TestCase):
    def test_parse_basic(self):
        m = parse_manifest("split: train\n\nid: a\ntext: hello\n")
        self.assertEqual(m.split, "train")
        self.assertEqual(len(m), 1)
        self.assertEqual(m.records[0].record_id, "a")
        self.assertEqual(m.records[0].text, "hello")

    def test_missing_split(self):
        with self.assertRaises(ManifestError):
            parse_manifest("id: a\ntext: hello\n")

    def test_duplicate_id(self):
        with self.assertRaises(ManifestError):
            parse_manifest("split: t\n\nid: a\ntext: x\n\nid: a\ntext: y\n")

    def test_missing_text(self):
        with self.assertRaises(ManifestError):
            parse_manifest("split: t\n\nid: a\n")

    def test_comments_ignored(self):
        m = parse_manifest("# note\nsplit: t\n\n# another\nid: a\ntext: hi\n")
        self.assertEqual(len(m), 1)


class NormaliseTests(unittest.TestCase):
    def test_whitespace(self):
        cfg = NormaliseConfig(whitespace=True, case=False, punctuation=False)
        self.assertEqual(normalise("a\t b\n  c", cfg), "a b c")

    def test_case(self):
        cfg = NormaliseConfig(whitespace=False, case=True, punctuation=False)
        self.assertEqual(normalise("ABC", cfg), "abc")

    def test_punctuation(self):
        cfg = NormaliseConfig(whitespace=True, case=False, punctuation=True)
        self.assertEqual(normalise("a, b! c.", cfg), "a b c")

    def test_none(self):
        cfg = NormaliseConfig(False, False, False)
        self.assertEqual(normalise("A, B ", cfg), "A, B ")
        self.assertEqual(cfg.describe(), "none")

    def test_digest_matches_after_normalisation(self):
        a = "Hello, WORLD!"
        b = "hello world"
        self.assertEqual(digest(a), digest(b))

    def test_describe(self):
        self.assertEqual(NormaliseConfig().describe(), "whitespace,case,punctuation")


class ShingleTests(unittest.TestCase):
    def test_shingles_count(self):
        s = shingles("abcdef", k=3)
        self.assertEqual(s, {"abc", "bcd", "cde", "def"})

    def test_short_text(self):
        self.assertEqual(shingles("ab", k=5), {"ab"})
        self.assertEqual(shingles("", k=5), set())

    def test_minhash_identical(self):
        s = shingles("the quick brown fox jumps", k=4)
        a = MinHash.from_shingles(s)
        b = MinHash.from_shingles(s)
        self.assertEqual(a.jaccard(b), 1.0)

    def test_minhash_disjoint(self):
        a = MinHash.from_shingles(shingles("aaaaaaaaaa", k=3))
        b = MinHash.from_shingles(shingles("zzzzzzzzzz", k=3))
        self.assertEqual(a.jaccard(b), 0.0)

    def test_minhash_estimate_within_error(self):
        # The MinHash estimate should be close to the exact Jaccard.
        text_a = "the mitochondria is the powerhouse of the cell"
        text_b = "the mitochondria is the powerhouse of the cel"
        sa = shingles(text_a, k=5)
        sb = shingles(text_b, k=5)
        exact = exact_jaccard(sa, sb)
        est = MinHash.from_shingles(sa, 256).jaccard(MinHash.from_shingles(sb, 256))
        # Standard error for MinHash is about 1/sqrt(num_perm); allow a margin.
        self.assertLess(abs(exact - est), 0.15)

    def test_minhash_deterministic(self):
        s = shingles("determinism matters here", k=4)
        self.assertEqual(
            MinHash.from_shingles(s).signature,
            MinHash.from_shingles(s).signature,
        )


class ContainmentTests(unittest.TestCase):
    def test_prefix(self):
        pos = find_containment(
            "water boils at one hundred degrees",
            "water boils at one hundred degrees celsius at standard pressure",
        )
        self.assertEqual(pos, "prefix")

    def test_interior(self):
        pos = find_containment(
            "powerhouse of the cell here",
            "the mitochondria is the powerhouse of the cell here indeed",
        )
        self.assertEqual(pos, "interior")

    def test_too_short_ignored(self):
        self.assertIsNone(find_containment("a b", "a b c d e f g h"))

    def test_equal_is_not_containment(self):
        self.assertIsNone(find_containment("identical text here", "identical text here"))


class OverlapTests(unittest.TestCase):
    def _load(self):
        from evalleak.records import load_manifest

        return [
            load_manifest(_sample("train.manifest")),
            load_manifest(_sample("validation.manifest")),
            load_manifest(_sample("test.manifest")),
        ]

    def test_all_finding_kinds_present(self):
        report = compare(self._load())
        self.assertEqual(len(report.exact), 1)
        self.assertEqual(len(report.near), 1)
        self.assertEqual(len(report.containment), 1)
        self.assertEqual(len(report.intra), 1)

    def test_exact_pair(self):
        report = compare(self._load())
        m = report.exact[0]
        self.assertEqual((m.split_a, m.id_a), ("test", "e1"))
        self.assertEqual((m.split_b, m.id_b), ("train", "t2"))

    def test_near_above_threshold(self):
        report = compare(self._load())
        self.assertGreaterEqual(report.near[0].jaccard, 0.6)

    def test_containment_pair(self):
        report = compare(self._load())
        c = report.containment[0]
        self.assertEqual((c.split_short, c.id_short), ("test", "e2"))
        self.assertEqual((c.split_long, c.id_long), ("train", "t5"))
        self.assertEqual(c.position, "prefix")

    def test_intra_pair(self):
        report = compare(self._load())
        d = report.intra[0]
        self.assertEqual(d.split, "train")
        self.assertEqual({d.id_a, d.id_b}, {"t3", "t6"})

    def test_total_contaminated(self):
        report = compare(self._load())
        self.assertEqual(report.total_contaminated(), 8)

    def test_deterministic_output(self):
        a = render_report(compare(self._load()))
        b = render_report(compare(self._load()))
        self.assertEqual(a, b)

    def test_no_findings_when_disjoint(self):
        from evalleak.records import parse_manifest

        m1 = parse_manifest("split: a\n\nid: x\ntext: apples grow on tall trees\n")
        m2 = parse_manifest("split: b\n\nid: y\ntext: rockets travel through space\n")
        report = compare([m1, m2])
        self.assertFalse(report.has_findings())

