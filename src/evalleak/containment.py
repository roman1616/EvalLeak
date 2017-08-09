"""Substring containment detection.

Exact and near duplicate checks compare whole records. They miss the case where
a short evaluation item is embedded inside a longer training record: a question
that appears verbatim as one paragraph of a longer document, for example. The
evaluation item is fully present in the training data, so the model may have
