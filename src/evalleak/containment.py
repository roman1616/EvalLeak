"""Substring containment detection.

Exact and near duplicate checks compare whole records. They miss the case where
a short evaluation item is embedded inside a longer training record: a question
that appears verbatim as one paragraph of a longer document, for example. The
evaluation item is fully present in the training data, so the model may have
seen the answer, yet neither the digest nor the Jaccard of the whole records
matches.

This module detects that. For an ordered pair (short, long) it reports
containment when the normalised short text is a substring of the normalised
long text. It classifies the position as prefix, suffix, or interior so a
