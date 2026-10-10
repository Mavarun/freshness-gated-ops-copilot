# Passage-level answer support: out-of-sample check (Stack Exchange test questions)

Trained on 18,888 train-split questions (56,664 rows: own answer, a hard negative sharing words, a random answer); evaluated on 2,066 hash-held-out test questions the vectors and the classifier never saw.

| scorer | AUC own vs hard negative | AUC own vs random | P@1 of 50 | MRR | P@1, own answer shares no title word (n) |
| --- | ---: | ---: | ---: | ---: | ---: |
| lexical coverage only | 0.629 | 0.888 | 0.653 | 0.729 | 0.000 (130) |
| classifier, lexical features | 0.640 | 0.873 | 0.640 | 0.716 | 0.000 (130) |
| classifier (+ domain vectors) | 0.711 | 0.901 | 0.679 | 0.770 | 0.100 (130) |

Chance P@1 is 0.020. Coefficients (standardised features): `lex` +1.93, `soft` -0.38, `weakest` +0.06, `missing` +0.96, `centroid` +0.88, intercept -0.22.
