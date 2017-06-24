"""Split manifest parsing.

A manifest is a small line-oriented text format, one record per logical block,
that names a split and lists its records. It was chosen over JSON so the
fixtures stay readable in a diff and so a record body can contain arbitrary
punctuation without escaping.

Format:

    # comment lines start with a hash and are ignored
    split: <name>

    id: <record id>
