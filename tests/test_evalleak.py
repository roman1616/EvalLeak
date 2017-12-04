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
