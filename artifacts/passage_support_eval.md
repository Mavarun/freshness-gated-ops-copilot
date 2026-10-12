# Passage-level answer support: out-of-sample check (Stack Exchange test questions)

Trained on 18,888 train-split questions (56,664 rows: own answer, a hard negative sharing words, a random answer); evaluated on 2,066 hash-held-out test questions the vectors and the classifier never saw.

| scorer | AUC own vs hard negative | AUC own vs random | P@1 of 50 | MRR | P@1, own answer shares no title word (n) |
| --- | ---: | ---: | ---: | ---: | ---: |
| lexical coverage only | 0.629 | 0.888 | 0.653 | 0.729 | 0.000 (130) |
| classifier, lexical features | 0.715 | 0.892 | 0.519 | 0.632 | 0.069 (130) |
| classifier (+ domain vectors) | 0.759 | 0.910 | 0.573 | 0.696 | 0.146 (130) |

Chance P@1 is 0.020. Coefficients (standardised features): `lex` +1.76, `soft` -0.15, `weakest` +0.04, `missing` +0.58, `centroid` +0.75, `jaccard` +0.42, `hit_frac` -0.58, `soft_ge_04` -0.15, `soft_ge_06` +0.38, `best_mean` +0.02, `len_ratio` -0.52, intercept -0.26.
