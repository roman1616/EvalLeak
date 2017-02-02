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
