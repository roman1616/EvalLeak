"""Line-oriented rendering of overlap findings.

Every renderer returns a list of strings, one per output line, so results diff
cleanly in git and are easy to test. No wall-clock time or randomness appears
in the output, so identical input produces byte-identical output.
"""

from __future__ import annotations

from .overlap import OverlapReport

