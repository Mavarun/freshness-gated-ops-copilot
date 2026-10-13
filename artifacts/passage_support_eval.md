# Passage-level answer support: out-of-sample check (Stack Exchange test questions)

Trained on 18,888 train-split questions (94,440 rows: own answer, a length-matched hard negative sharing words, 3 random answer(s); recipe chosen on validation questions only); evaluated on 2,066 hash-held-out test questions the vectors and the classifier never saw.

`vs hard` uses the PR #19 max-coverage hard negatives (median 61 distinct words vs 41 for real answers); `vs hard (len)` uses length-matched ones, where length carries no signal.

| scorer | AUC vs hard | AUC vs hard (len) | AUC vs random | P@1 of 50 | MRR | P@1, own answer shares no title word (n) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| lexical coverage only | 0.629 | 0.734 | 0.888 | 0.653 | 0.729 | 0.000 (130) |
| classifier, lexical features | 0.689 | 0.766 | 0.905 | 0.641 | 0.725 | 0.038 (130) |
| classifier (+ vectors), PR #19 max-coverage negatives | 0.759 | 0.814 | 0.910 | 0.573 | 0.696 | 0.146 (130) |
| classifier (+ vectors), length_matched/r3/b1.5 | 0.731 | 0.807 | 0.923 | 0.692 | 0.777 | 0.131 (130) |

Chance P@1 is 0.020. Coefficients (standardised features): `lex` +1.91, `soft` +0.03, `weakest` -0.03, `missing` +0.40, `centroid` +0.83, `jaccard` +0.44, `hit_frac` -0.40, `soft_ge_04` -0.08, `soft_ge_06` +0.52, `best_mean` -0.39, `len_ratio` -0.48, intercept -0.73.
