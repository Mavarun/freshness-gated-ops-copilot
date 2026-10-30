# Passphrase list / purpose arms: calibration (seed 3010, 1,200 EFF rows; 3,020 SE train sentences, 1,867 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_compound_protocol`. Arm = compound list mode / space list arm / purpose trailing number. `none/-/-` is the shipped detector. The shipped detector already flags 221 of the 1,867 train identifiers; the identifier column counts flags on top of those.

| arm | leak rows | leak words | over words | SE sentences flagged | SE identifiers newly flagged | Oct 13 leaks | repo query changes | data/ ids new | safe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| none/-/- | 28 | 136 | 533 | 28 | 0 | 0 | 0 | 0 | yes |
| none/-/num | 18 | 77 | 533 | 28 | 0 | 0 | 0 | 0 | yes |
| none/space/- | 27 | 132 | 535 | 28 | 0 | 0 | 0 | 0 | yes |
| none/space/num | 17 | 73 | 535 | 28 | 0 | 0 | 0 | 0 | yes |
| all4/-/- | 20 | 100 | 533 | 28 | 0 | 0 | 0 | 0 | yes |
| all4/-/num | 10 | 41 | 533 | 28 | 0 | 0 | 0 | 0 | yes |
| all4/space/- | 19 | 96 | 535 | 28 | 0 | 0 | 0 | 0 | yes |
| all4/space/num | 9 | 37 | 535 | 28 | 0 | 0 | 0 | 0 | yes |
| but1_4/-/- | 20 | 100 | 533 | 28 | 16 | 0 | 0 | 0 | no: ident_budget |
| but1_4/-/num | 10 | 41 | 533 | 28 | 16 | 0 | 0 | 0 | no: ident_budget |
| but1_4/space/- | 19 | 96 | 535 | 28 | 16 | 0 | 0 | 0 | no: ident_budget |
| but1_4/space/num | 9 | 37 | 535 | 28 | 16 | 0 | 0 | 0 | no: ident_budget |
| all3/-/- | 20 | 100 | 533 | 28 | 28 | 0 | 0 | 0 | no: ident_budget |
| all3/-/num | 10 | 41 | 533 | 28 | 28 | 0 | 0 | 0 | no: ident_budget |
| all3/space/- | 19 | 96 | 535 | 28 | 28 | 0 | 0 | 0 | no: ident_budget |
| all3/space/num | 9 | 37 | 535 | 28 | 28 | 0 | 0 | 0 | no: ident_budget |

**Chosen:** `all4/space/num`

Leak causes, shipped: no_flag_ops 8, other 14, stop_inside 6

Leak causes, chosen: other 3, stop_inside 6
