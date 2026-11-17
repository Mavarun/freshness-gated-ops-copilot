# Citation-aware non-key protocol, calibration re-score (golden + dev2-dev6 + dev8)

320 rows; the Nov 7 384 swaps (3 random corpus words per salient term, seed 1107). Budget lost = right-evidence losses + losses on rows without an evidence label; a refused wrong-evidence answer is fixed, not lost. This re-scores a calibration that was already seen (see the protocol docstring).

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | decision lost | fixed (wrong evidence) | budget lost | new wrong evidence | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 54/165 | 0 | 0 | 0 | 0 | 8/144 |
| `all` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 49/165 | 5 | 1 | 4 | 0 | 5/144 |
| `all_hyphen` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 1 | 2 | 0 | 5/144 |
| `all_joined` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 1 | 2 | 0 | 5/144 |
| `corpus_hyphen` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 1 | 2 | 0 | 5/144 |

- `all`: lost d5-22; fixed d6-06; unlabelled lost d8-06, d8-29, d8-30; new wrong evidence none
- `all_hyphen`: lost d5-22; fixed d6-06; unlabelled lost d8-30; new wrong evidence none
- `all_joined`: lost d5-22; fixed d6-06; unlabelled lost d8-30; new wrong evidence none
- `corpus_hyphen`: lost d5-22; fixed d6-06; unlabelled lost d8-30; new wrong evidence none

`all` is the Nov 9 reference and cannot be picked. Picked: `all_hyphen` (expected before the re-score: `all_hyphen`).
