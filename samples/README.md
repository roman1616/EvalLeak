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
