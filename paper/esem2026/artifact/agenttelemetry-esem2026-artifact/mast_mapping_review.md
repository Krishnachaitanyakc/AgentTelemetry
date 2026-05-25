# Dual-Coding Review

The second annotator independently coded the 13 MAST-mapped benchmark faults. cost_explosion is excluded from kappa because it is not a MAST label.

| statistic | value |
|---|---:|
| coded items | 13 |
| observed agreement | 11/13 = 0.846 |
| kappa used in paper | 0.83 |
| bootstrap 95% CI | [0.58, 1.00] |
| resamples | 10,000 |
| RNG seed | 20260506 |

Two disagreements involved adjacent MAST categories for context/reasoning failures. They were resolved by consensus before detector scoring. The paper reports the agreement statistic before consensus.

The item-level labels are in `mast_mapping_review.tsv`.
