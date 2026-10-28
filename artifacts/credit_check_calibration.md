# Credited-word check: calibration grid (pre-registered, `credit_check.py`)

Rows: 238 calibration ({'dev': 15, 'dev2': 43, 'dev3': 45, 'dev4': 44, 'dev5_tune': 24, 'dev6': 45, 'dev7_tune': 22}), 51 clean, 95 traps (36 v1 + 40 v2 + 19 v3 tune). Baseline (shipped default): 114/238 (ANSWER 28/125), traps opened at2-01, must-refuse opened none.

Safe = clean 1.000, no must-refuse row or calibration trap opened, sweep safe, at most 6 rows / 3 ANSWER lost. Rows sorted by the selection key.

| arm | safe | calib correct | ANSWER | rows lost | new errors | traps opened | must-refuse opened |
| :--- | :---: | ---: | ---: | ---: | :--- | :--- | :--- |
| stop | yes | 110 | 25 | 4 | d3-02, d4-43, d5-18, d6-09 | - | - |
| stop + rank<=2000 | yes | 110 | 25 | 4 | d3-02, d4-43, d5-18, d6-09 | - | - |
| rank<=2000 | no | 113 | 27 | 1 | d3-02 | at2-01 | - |
| rank<=1000 | no | 110 | 24 | 4 | d2-14, d2-17, d3-02, d5-18 | at2-01 | - |
| stop + rank<=1000 | no | 108 | 23 | 6 | d2-14, d2-17, d3-02, d4-43, d5-18, d6-09 | - | - |
| top50 | no | 105 | 21 | 9 | d2-15, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top50 + rank<=2000 | no | 105 | 21 | 9 | d2-15, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top50 | no | 105 | 21 | 9 | d2-15, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top50 + rank<=2000 | no | 105 | 21 | 9 | d2-15, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| rank<=500 | no | 105 | 20 | 9 | d2-09, d2-14, d2-17, d3-02, d3-10, d3-30, d4-10, d5-18, d6-09 | - | - |
| stop + rank<=500 | no | 104 | 20 | 10 | d2-09, d2-14, d2-17, d3-02, d3-10, d3-30, d4-10, d4-43, d5-18, d6-09 | - | - |
| top50 + rank<=1000 | no | 103 | 19 | 11 | d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top50 + rank<=1000 | no | 103 | 19 | 11 | d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top100 | no | 102 | 18 | 12 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top100 + rank<=2000 | no | 102 | 18 | 12 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top100 | no | 102 | 18 | 12 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top100 + rank<=2000 | no | 102 | 18 | 12 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top100 + rank<=1000 | no | 100 | 16 | 14 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top100 + rank<=1000 | no | 100 | 16 | 14 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d3-21, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top200 | no | 99 | 16 | 15 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| top50 + rank<=500 | no | 99 | 16 | 15 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-30, d4-10, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top200 + rank<=2000 | no | 99 | 16 | 15 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| stop + top200 | no | 99 | 16 | 15 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| stop + top50 + rank<=500 | no | 99 | 16 | 15 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-30, d4-10, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top200 + rank<=2000 | no | 99 | 16 | 15 | d2-09, d2-15, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| top100 + rank<=500 | no | 97 | 14 | 17 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-21, d3-30, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| top200 + rank<=1000 | no | 97 | 14 | 17 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| stop + top100 + rank<=500 | no | 97 | 14 | 17 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-21, d3-30, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g48-synonym | - | - |
| stop + top200 + rank<=1000 | no | 97 | 14 | 17 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-18, d3-19, d3-21, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| top200 + rank<=500 | no | 95 | 13 | 19 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-21, d3-30, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |
| stop + top200 + rank<=500 | no | 95 | 13 | 19 | d2-09, d2-14, d2-15, d2-17, d3-02, d3-10, d3-18, d3-19, d3-21, d3-30, d4-10, d4-21, d4-43, d5-18, d6-09, d6-20, g35-synonym, g39-synonym, g48-synonym | - | - |

2 of 31 settings safe. **Chosen: stop** (110/238, 4 rows lost).
