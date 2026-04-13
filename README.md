<h1 align="left">EvalLeak</h1>

EvalLeak detects contamination between training and evaluation splits by finding
exact duplicates, near duplicates, and containment across split manifests of text
records.

```
$ PYTHONPATH=src python -m EvalLeak report samples/train.manifest samples/validation.manifest samples/test.manifest
EvalLeak contamination report
normalisation: whitespace,case,punctuation

split record counts:
  test: 3
  train: 6
  validation: 3

exact cross-split duplicates:
  test/e1 == train/t2  digest=61b2a8f4c53e

near cross-split duplicates (jaccard >= 0.60, k=5, num_perm=128):
  train/t1 ~ validation/v1  jaccard~=0.883

containment (min_length=16):
  test/e2 inside train/t5  position=prefix

intra-split duplicates:
  train/t3 == train/t6  digest=d9efde07fef6

contamination rate per split pair (source -> target):
  test -> train: 2/6 = 33.33%
  train -> test: 2/3 = 66.67%
  train -> validation: 1/3 = 33.33%
  validation -> train: 1/6 = 16.67%

total contaminated records: 8
```

> The sample corpus has 8 distinct contaminated records across its three splits.

## Contents

- [The problem](#the-problem)
- [What EvalLeak checks](#what-evalleak-checks)
- [Install and run](#install-and-run)
- [The four detectors](#the-four-detectors)
- [A worked walkthrough](#a-worked-walkthrough)
- [Reading the report](#reading-the-report)
- [Report format, field by field](#report-format-field-by-field)
- [Exit codes](#exit-codes)
- [Normalisation, and why each step is switchable](#normalisation-and-why-each-step-is-switchable)
- [Design decisions](#design-decisions)
- [The split overlap graphic](#the-split-overlap-graphic)
- [Repository layout](#repository-layout)
- [Glossary](#glossary)
- [Integration notes](#integration-notes)
- [Verification](#verification)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [License](#license)

## The problem

You train a model, you evaluate it on a held-out split, and the numbers look
good. Then someone asks whether any evaluation item was already in the training
data. If it was, the score measures memorisation, not generalisation, and the
result is worthless for deciding whether to ship.

Contamination is easy to introduce and hard to see. A dataset is assembled from
several sources, deduplicated loosely or not at all, then split into train,
validation, and test. The same paragraph can arrive through two sources with
different whitespace, different capitalisation, or a stray edit, and land on
both sides of the split. A question can appear on its own in the test set and
also as one paragraph inside a longer training document. None of this is visible
by eye once the corpus passes a few hundred records.

EvalLeak reads the split manifests and reports exactly which records overlap,
naming the record ids, so the finding is actionable. An aggregate rate tells you
that you have a problem. It does not tell you which records to remove.

## What EvalLeak checks

Given two or more split manifests, EvalLeak runs four checks:

- Exact duplicates across splits, by normalised digest.
- Near duplicates across splits, by character shingling with a MinHash Jaccard
  estimate.
- Containment across splits, where a shorter evaluation item is a substring of a
  longer training record (prefix, suffix, or interior).
- Intra-split duplicates, exact duplicates inside one split, which inflate the
  apparent dataset size without adding information.

Every check is offline, deterministic, and built on the Python standard library
only. There is no network access anywhere in the code.

## Install and run

EvalLeak targets Python 3.11 and has no third-party runtime dependencies. Run it
straight from a checkout with the package on the path:

```
$ PYTHONPATH=src python -m EvalLeak version
EvalLeak 0.1.0
```

Or install it and use the console script:

```
pip install .
EvalLeak report split_a.manifest split_b.manifest
```

A manifest is a small line-oriented text file. It declares one split name, then
lists records, each with an id and a single line of text:

```
split: train

id: t1
text: The mitochondria is the powerhouse of the cell and supplies chemical energy.

id: t2
text: Photosynthesis converts light energy into chemical energy stored in glucose.
```

Comment lines begin with a hash. A record must have both an `id:` and a `text:`
line, and ids must be unique within a split. A malformed manifest is a usage
error, not a silent skip.

## The four detectors

The `exact` and `near` subcommands run one detector each and print just that
class of finding. The `report` subcommand runs all four and prints the full
picture, including the per-pair rates. Here are the two focused subcommands
against the samples:

```
$ PYTHONPATH=src python -m EvalLeak exact samples/train.manifest samples/validation.manifest samples/test.manifest
exact cross-split duplicates:
  test/e1 == train/t2  digest=61b2a8f4c53e
```

```
$ PYTHONPATH=src python -m EvalLeak near samples/train.manifest samples/validation.manifest samples/test.manifest
near cross-split duplicates (jaccard >= 0.60, k=5, num_perm=128):
  train/t1 ~ validation/v1  jaccard~=0.883
```

Both subcommands exit 1 when they find anything, so a bare `exact` check is a
usable gate on its own.

## A worked walkthrough

Follow `validation/v1` through the pipeline. Its raw text is:

```
THE MITOCHONDRIA IS THE POWERHOUSE OF THE CELL, AND IT SUPPLIES CHEMICAL ENERGY!!!
```

The training record `train/t1` is:

```
The mitochondria is the powerhouse of the cell and supplies chemical energy.
```

First, normalisation runs with all three steps on. Whitespace is collapsed, case
is folded to lower, and ASCII punctuation is dropped and re-collapsed. Both
records become close but not identical, because `v1` still carries the inserted
word "it". So the sha256 digests differ, and the exact check does not fire.

Next, each normalised text is cut into character 5-shingles, the shingle sets are
reduced to 128-value MinHash signatures, and the signatures are compared. The
fraction of matching minima estimates the Jaccard similarity of the two shingle
sets, here about 0.883, which clears the 0.60 threshold. So `v1` is reported as a
near duplicate of `t1`.

Finally the pair contributes to the directional rates. Because `v1` is one of the
three validation records touched by a train record, the `train -> validation`
rate is 1 of 3, and because `t1` is one of six train records touched by a
validation record, the `validation -> train` rate is 1 of 6.

## Reading the report

Each finding class maps to a different action:

| Finding          | What it means                                              | Suggested action                                     |
|------------------|------------------------------------------------------------|------------------------------------------------------|
| exact            | Same text on both sides after normalisation                | Remove the record from the evaluation split          |
| near             | High Jaccard estimate, likely a light edit of the same text| Inspect the pair, then remove or keep with a note    |
| containment      | Evaluation item sits inside a longer training record       | Remove the item, or exclude the training passage     |
| intra-split      | Duplicate inside one split                                 | Deduplicate before reporting split sizes             |

The directional rates tell you where the damage lands. A high `train -> test`
rate is the worst case, because it inflates the headline score. A high
`test -> train` rate for the same pair is the same records viewed from the other
side, and the smaller denominator, the test split, is usually the number to act
on.

## Report format, field by field

The `report` output is line oriented so it diffs cleanly in git. The fields are:

| Section                  | Line shape                                             | Meaning                                                        |
|--------------------------|--------------------------------------------------------|----------------------------------------------------------------|
| header                   | `EvalLeak contamination report`                        | Fixed banner                                                   |
| normalisation            | `normalisation: whitespace,case,punctuation`           | The active normalisation steps for this run                    |
| split record counts      | `<split>: <n>`                                         | Records parsed from each manifest                              |
| exact cross-split        | `<a>/<id> == <b>/<id>  digest=<12 hex>`                | Two records with the same normalised digest                    |
| near cross-split         | `<a>/<id> ~ <b>/<id>  jaccard~=<0.000>`                | Estimated Jaccard at or above the threshold                    |
| containment              | `<a>/<id> inside <b>/<id>  position=<pos>`             | Short record contained in long record, with position          |
| intra-split              | `<split>/<id> == <split>/<id>  digest=<12 hex>`        | Duplicate inside one split                                     |
| contamination rate       | `<source> -> <target>: <c>/<t> = <pct>`                | Directional rate, contaminated over target size               |
| total                    | `total contaminated records: <n>`                      | Distinct records involved in any finding, across all splits    |

The digest is truncated to 12 hex characters for readability. The full sha256 is
computed internally; the prefix is enough to correlate two lines by eye.

## Exit codes

| Code | Meaning                                                         |
|------|-----------------------------------------------------------------|
| 0    | Clean, no findings for the subcommand that ran                  |
| 1    | Findings present                                                |
| 2    | Usage error, including a missing or malformed manifest          |

argparse itself exits with 2 on an unknown flag or a missing argument, which
matches the usage-error code.

## Normalisation, and why each step is switchable

Normalisation decides which records count as "the same", and it is the single
biggest lever on the result. More aggressive normalisation collapses more surface
differences and reports more contamination. Each step is a separate flag so the
aggressiveness is visible and so you can see which transformation caused a match:

| Step        | Flag to disable    | Effect                                             |
|-------------|--------------------|----------------------------------------------------|
| whitespace  | `--no-whitespace`  | Collapse every run of whitespace to one space      |
| case        | `--no-case`        | Lowercase the text                                 |
| punctuation | `--no-punctuation` | Drop ASCII punctuation, then re-collapse whitespace|

The default enables all three, the most aggressive setting. For contamination
detection that is the safer default: a borderline match a human can dismiss is
better than a real leak that is never seen. Turn steps off when you want to know
whether a match survives without that transformation. If `train/t1` and
`validation/v1` stop matching once punctuation removal is off, you have learned
that punctuation is doing the work, which is a weaker signal than a match that
survives every step.

## Design decisions

Line-oriented text manifests over JSON. The fixtures and the output both need to
diff cleanly, and a record body full of punctuation is awkward to keep readable
inside escaped JSON strings. The rejected alternative was JSON Lines, which is
more standard but harder to author and read by hand, and the whole point of the
sample fixtures is that a person can see the planted cases at a glance.

MinHash over exact Jaccard for the near check. Exact Jaccard needs the full
shingle set for every record and a set intersection for every pair, which is
quadratic in both records and record length. A MinHash signature is a fixed size
regardless of record length, and the comparison is a cheap count of matching
minima. The cost is an estimate with error bounds rather than an exact number.
The rejected alternative, exact Jaccard, is what the test suite uses to bound the
estimate error, so the trade is measured, not assumed.

hashlib for the MinHash permutations. A real MinHash usually draws random hash
coefficients. That would make the output depend on a seed, which breaks the
byte-identical determinism the project requires. Instead each of the 128
"permutations" is sha256 salted with its index, so the signature is a pure
function of the input. The rejected alternative, seeded randomness, would have
needed the seed recorded in the output and would still surprise anyone diffing
two runs.

Containment as normalised substring search, separate from the near check. A short
item inside a long document has a low whole-record Jaccard, because the long
document contributes many shingles the item does not share, so the near check
misses it. Substring search after normalisation catches it directly. The
`min_length` guard exists because a very short item is contained in almost any
document by chance, which would be noise, not contamination.

Directional rates rather than one symmetric number. Leaking a training record
into a small test split is far worse than the reverse, and a single symmetric
overlap number would hide the direction. Reporting both directions costs two
lines and keeps the asymmetry visible.

## The split overlap graphic

![Bar chart of record counts per split, train six, validation three, test three,
with a table of contamination findings between split pairs: train and test two,
train and validation one, validation and test zero.](docs/assets/split-overlap.svg)

Every number in the graphic comes from the `report` run shown at the top of this
file: the record counts per split, the count of cross-split findings for each
split pair, and the total of eight contaminated records. The bars use the slate
ink, and the one accent, amber, is reserved for the contamination edges, the
thing to look at first.

## Repository layout

```
EvalLeak/
  README.md                     this file
  LICENSE                       MIT, holder "the EvalLeak authors", 2026
  CHANGELOG.md                  release notes
  .gitignore                    ignore build and cache artefacts
  pyproject.toml                setuptools, src layout, console script
  src/EvalLeak/
    __init__.py                 package version
    __main__.py                 enables python -m EvalLeak
    cli.py                      argparse subcommands: exact, near, report, version
    records.py                  split manifest parsing
    normalise.py                switchable whitespace, case, punctuation steps
    shingle.py                  character k-shingles and a hashlib MinHash sketch
    containment.py              prefix, suffix, interior substring containment
    overlap.py                  pairwise comparison and directional rates
    report.py                   line-oriented rendering
  tests/
    test_evalleak.py            unittest suite, 35 tests
  samples/
    README.md                   how each fixture was constructed
    train.manifest              six records, includes one intra-split duplicate
    validation.manifest         three records, includes one near duplicate
    test.manifest               three records, includes exact and containment cases
  docs/assets/
    logo.svg                    wordmark, colour split at the eval|leak boundary
    split-overlap.svg           record counts and contamination, real numbers
```

## Glossary

- Split: a named partition of a dataset, such as train, validation, or test.
- Manifest: the text file that declares one split and lists its records.
- Record: one text item in a split, with an id and a body.
- Normalisation: the whitespace, case, and punctuation transforms applied before
  comparison.
- Digest: the sha256 hash of a record's normalised text. Equal digests mean an
  exact duplicate under the current normalisation.
- Shingle: a fixed-length substring. EvalLeak uses character 5-shingles by
  default.
- Jaccard similarity: the size of the intersection over the size of the union of
  two sets. Here, the sets of shingles.
- MinHash: a fixed-size signature whose matching-minima fraction estimates the
  Jaccard similarity.
- Containment: the case where one record's normalised text is a substring of
  another's.
- Contamination rate: contaminated records in a target split over the target
  split size, reported per direction.

## Integration notes

EvalLeak is a gate. In CI, run it over your split manifests and let the exit code
fail the job:

```
PYTHONPATH=src python -m EvalLeak report train.manifest val.manifest test.manifest
```

A zero exit means clean, a one means findings, and a two means the manifests
could not be parsed. Because the output is deterministic and line oriented, you
can commit a known-good report and diff future runs against it in git to see
exactly which records changed. To compare two runs, redirect each to a file and
diff them; new or removed finding lines are the signal.

## Verification

The four project checks were run in this session:

```
$ PYTHONPATH=src python -m unittest discover -s tests -v
...
Ran 35 tests in 0.862s

OK
```

The 35 tests cover manifest parsing and its error cases, each normalisation step
in isolation, shingle construction on short and long text, the MinHash estimate
against the exact Jaccard within an error margin, containment position
classification, the full overlap over the samples, deterministic output, and the
CLI exit codes.

The CLI was run end to end against `samples/` and its real output is pasted at the
top of this file and in the detector sections. Both SVG assets under
`docs/assets/` parse as XML. A search across the whole project for the em dash
character returns nothing.

## Limitations

Read these before trusting a clean report.

- A MinHash Jaccard is an estimate, not the true value. With 128 permutations the
  standard error is roughly one over the square root of 128, about 0.09, so a
  near duplicate can sit just above or just below the threshold by chance. Raise
  `--num-perm` to tighten the estimate at a linear cost in time.
- Normalisation choices change the answer. A match reported with all steps on may
  vanish with punctuation removal off. The report prints the active steps so the
  setting is never hidden, but there is no single correct setting.
- Semantic duplication is not detected at all. Two records that say the same thing
  in different words share no shingles and produce no finding. EvalLeak measures
  textual overlap, not meaning. A paraphrase leak is invisible to it.
- Containment uses a length guard, so a genuinely short evaluation item can slip
  under `min_length` and go unreported. Lower the guard only if you accept more
  coincidental matches.
- The comparison is pairwise and quadratic in the number of records per split
  pair. It is built for split manifests of manageable size, not for deduplicating
  a corpus of millions of records.

## Roadmap

No dates. In rough priority order:

- A blocking mode that shards records to reduce the quadratic pair count.
- A JSON output mode alongside the line-oriented text, for machine consumers.
- Token shingling as an option next to character shingling.
- A diff subcommand that compares two report files directly.

## License

MIT. See [LICENSE](LICENSE).

<p align="right">
  <img src="docs/assets/logo.svg" width="200"
       alt="EvalLeak wordmark with eval in slate and leak in amber, split at the
       morpheme boundary above a baseline rule">
</p>

## Installation

EvalLeak is a single-package install with zero dependencies:

```bash
pip install .
```

Python 3.11+ recommended; the scanner only uses the standard library.

## Quick start

```bash
# check one manifest pair for overlap
evalleak check train.manifest validation.manifest

# full report across every split at once
evalleak report train.manifest validation.manifest test.manifest
```

Exit code is non-zero when the containment rate exceeds the configured
threshold, so the command drops straight into CI.

## How splitting works

Every record is reduced to a canonical form first: whitespace is normalised,
line endings are folded, and text is shingled into overlapping n-grams. Two
records are considered overlapping when their shingle Jaccard similarity
crosses the configured threshold - exact-duplicate detection falls out of
that naturally at threshold 1.0.

Near-duplicate handling is deliberately conservative: paraphrases that share
structure but not shingles are NOT flagged. The tool prefers a low false
positive rate over catching clever rewrites; if you need that, raise the
shingle size and accept the noise.

## Interpreting the report

- **containment** - fraction of the eval split covered by train. Above ~2%
  your headline numbers are optimistic.
- **overlap pairs** - the concrete (train_id, eval_id) matches, sorted by
  similarity, with the shared shingle count attached.
- **per-source rollup** - overlap grouped by the source field, which usually
  names the crawler or dataset that caused the leak.

## FAQ

**Does it handle JSONL and plain text manifests?**
Both. Records are line-delimited; any field can be selected as the text body
via the --text-field flag.

**Why not embeddings?**
Deterministic shingles keep the scan reproducible and dependency-free. An
embedding pass would make the tool slower, add a model download, and make
two runs of the same tree disagree.

**CI usage?**
valleak check with --max-containment 2.0 fails the job on contamination
above 2 percent and prints the offending pairs.
# draft note 47
