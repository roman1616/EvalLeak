"""Character k-shingles and a MinHash sketch for a Jaccard estimate.

Two records rarely match byte for byte after an edit, so exact digest matching
misses near duplicates. Character k-shingling turns each record into the set of
its length-k substrings, and the Jaccard similarity of two such sets measures
how much text they share regardless of small edits.

Computing exact Jaccard needs both full sets in memory and a set intersection
per pair, which is quadratic in the number of records. A MinHash sketch trades
