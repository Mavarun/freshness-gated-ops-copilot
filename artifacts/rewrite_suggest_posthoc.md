# Verified rewrites, post-hoc strict anchors (does not change the ship call)

Confirm arm `context_mc2` shipped **off**. Strict = gold word placed in the slot of the word the user typed.

| set | arm | rescuable | anchor_hit_3 | strict_anchor_hit_3 | trap_invitation |
| :--- | :--- | ---: | ---: | ---: | ---: |
| calibration | `idf` | 93 | 32 | 32 | 0.500 |
| calibration | `first` | 93 | 27 | 27 | 0.548 |
| calibration | `context` | 93 | 50 | 50 | 0.548 |
| calibration | `context_mc1` | 93 | 41 | 41 | 0.548 |
| calibration | `context_mc2` | 93 | 41 | 41 | 0.286 |
| calibration | `context_pairs` | 93 | 50 | 50 | 0.786 |
| calibration | `context_mc1_pairs` | 93 | 41 | 41 | 0.786 |
| dev7+fresh | `idf` | 33 | 13 | 13 | 0.500 |
| dev7+fresh | `first` | 33 | 10 | 10 | 0.500 |
| dev7+fresh | `context` | 33 | 20 | 20 | 0.500 |
| dev7+fresh | `context_mc1` | 33 | 18 | 18 | 0.500 |
| dev7+fresh | `context_mc2` | 33 | 18 | 18 | 0.300 |
| dev7+fresh | `context_pairs` | 33 | 20 | 20 | 0.800 |
| dev7+fresh | `context_mc1_pairs` | 33 | 18 | 18 | 0.800 |
| heldout | `idf` | 9 | 3 | 2 | 0.250 |
| heldout | `first` | 9 | 4 | 1 | 0.250 |
| heldout | `context` | 9 | 4 | 3 | 0.250 |
| heldout | `context_mc1` | 9 | 3 | 2 | 0.250 |
| heldout | `context_mc2` | 9 | 2 | 1 | 0.250 |
| heldout | `context_pairs` | 9 | 6 | 4 | 0.500 |
| heldout | `context_mc1_pairs` | 9 | 5 | 4 | 0.500 |
