# Noun gloss-sense calibration (ops noun + Wiktionary all-POS bridges)

Clean golden: 51 rows. Dev synonym: 15 rows (held-out never scored). Off baseline: clean 1.000, dev synonym 0.800.

Chosen: min_gloss_cosine **0.85**, max_neighbours **2**, min_score **1.1** (clean 1.000, dev synonym 0.800, dev ANSWER 3/5; 12 of 24 settings safe). Calibration candidate for default-on: **True**. The held-out run is the go / no-go.

