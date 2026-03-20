# Sample fixtures

These three manifests are hand-authored test vectors, not production data. They
exist to exercise every detector in evalleak with a known, checkable answer.
Each record body is a short, factual sentence written for this repository.

## Files

- `train.manifest`, split `train`, six records.
- `validation.manifest`, split `validation`, three records.
- `test.manifest`, split `test`, three records.

## What each planted case demonstrates

- Exact cross-split duplicate: `test/e1` and `train/t2` are the same sentence
  about photosynthesis, so they share a normalised digest.
- Near duplicate: `validation/v1` is `train/t1` rewritten in upper case, with
  extra punctuation, and with the single word "IT" inserted. The punctuation
  and case differences are erased by normalisation, but the inserted word keeps
  it below an exact match, so it surfaces as a near duplicate rather than an
  exact one. Estimated Jaccard is about 0.88 with the default settings.
- Containment: `test/e2` is a sentence about the boiling point of water that
  appears verbatim as the opening of the longer `train/t5` record, so it is
  reported as a prefix containment.
- Intra-split duplicate: `train/t3` and `train/t6` are the same sentence about
  binary search, inside the same split, which inflates the apparent train size.

## Reproducing the numbers

Run from the project root with the package on the path:

```
set PYTHONPATH=src
python -m evalleak report samples\train.manifest samples\validation.manifest samples\test.manifest
```

The report prints one exact, one near, one containment, and one intra-split
finding, and a total of eight distinct contaminated records.

# draft note 31
