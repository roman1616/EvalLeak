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
