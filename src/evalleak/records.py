"""Split manifest parsing.

A manifest is a small line-oriented text format, one record per logical block,
that names a split and lists its records. It was chosen over JSON so the
fixtures stay readable in a diff and so a record body can contain arbitrary
punctuation without escaping.

Format:

    # comment lines start with a hash and are ignored
    split: <name>

    id: <record id>
    text: <one line of text>

    id: <record id>
    text: <one line of text>

Every record has a unique id within its split. The split name is declared once
at the top with the `split:` key. Blank lines separate records. A record needs
both an `id:` and a `text:` line; a record missing either raises ManifestError
so a malformed fixture fails loudly instead of silently dropping data.
"""

from __future__ import annotations

from dataclasses import dataclass


class ManifestError(ValueError):
    """Raised when a manifest cannot be parsed into a clean set of records."""


@dataclass(frozen=True)
class Record:
    """One text record inside a split."""

    split: str
    record_id: str
    text: str


@dataclass(frozen=True)
class Manifest:
    """A named split and its records, in file order."""

    split: str
    records: tuple[Record, ...]

    def __len__(self) -> int:
        return len(self.records)


