# Passage classifier: training-recipe selection (validation questions only)

Fitted on 16,978 train-minus-validation questions, scored on 1,910 validation questions. Test questions were not loaded.

Hard-negative length on the fit split (distinct words, median): max_lex: own 41 / hard 66, length_matched: own 41 / hard 44.

Rule: AUC vs length-matched hard >= baseline - 0.005, then max MRR.

| recipe | AUC vs hard | AUC vs length-matched hard | P@1 of 50 | MRR | no-shared-word P@1 (n) | kept |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| `max_lex/r1/b1.5` | 0.778 | 0.827 | 0.639 | 0.746 | 0.140 (121) | yes |
| `max_lex/r2/b1.5` | 0.771 | 0.827 | 0.676 | 0.774 | 0.099 (121) | yes |
| `max_lex/r3/b1.5` | 0.766 | 0.826 | 0.700 | 0.789 | 0.107 (121) | yes |
| `length_matched/r1/b1.25` | 0.765 | 0.825 | 0.702 | 0.790 | 0.107 (121) | yes |
| `length_matched/r1/b1.5` | 0.765 | 0.826 | 0.704 | 0.791 | 0.107 (121) | yes |
| `length_matched/r1/b2.0` | 0.768 | 0.827 | 0.693 | 0.783 | 0.124 (121) | yes |
| `length_matched/r2/b1.25` | 0.759 | 0.824 | 0.719 | 0.800 | 0.091 (121) | yes |
| `length_matched/r2/b1.5` | 0.760 | 0.825 | 0.720 | 0.800 | 0.107 (121) | yes |
| `length_matched/r2/b2.0` | 0.763 | 0.826 | 0.709 | 0.794 | 0.107 (121) | yes |
| `length_matched/r3/b1.25` | 0.757 | 0.823 | 0.722 | 0.802 | 0.083 (121) | yes |
| `length_matched/r3/b1.5` | 0.758 | 0.823 | 0.724 | 0.803 | 0.091 (121) | **chosen** |
| `length_matched/r3/b2.0` | 0.760 | 0.824 | 0.720 | 0.801 | 0.107 (121) | yes |
