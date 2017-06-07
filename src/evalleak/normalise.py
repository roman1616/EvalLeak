"""Text normalisation with each step individually switchable.

Normalisation decides which records count as "the same". A more aggressive
setting collapses more surface differences and therefore reports more
contamination. Making each step a separate flag keeps that trade off visible:
you can see exactly which transformation caused two records to match.

Steps, applied in this fixed order when enabled:
