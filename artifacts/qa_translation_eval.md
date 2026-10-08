# QA translation model: out-of-sample answer ranking (outside data)

Model: IBM Model 1, question <- answer, 3 EM iterations (picked by validation MRR over [1, 2, 3, 5, 8] on a hash slice of train), trained on 32,513 (title, answer) pairs from 20,954 most-voted questions of 8 ops Stack Exchange sites (CC BY-SA). Test: 3,597 pairs of the hash-held-out 10% of questions, never seen in training.

Task: rank each test question's own answer among 50 candidates (the others are answers to other test questions, seed 42); 1000 test questions. 14.9% of true answers share no content word with their title.

| scorer | P@1 | MRR | P@1 when the answer shares no title word |
| --- | ---: | ---: | ---: |
| bm25 | 0.682 | 0.738 | 0.000 |
| translation | 0.712 | 0.786 | 0.134 |
| combined | 0.677 | 0.759 | 0.020 |

Chance P@1 is 0.020. Training took 3 s, the ranking eval 113 s (box CPU). Table: 374 corpus words x top question words (32,721 entries), SHA-256 `8357261f4f314f5d37a3e983ae519e6773eb3439a531bc9788deb1217227e0b6`.
