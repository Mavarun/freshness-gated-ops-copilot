# Passphrase tail / incoherence arm: amended one-shot confirm (seed 2931, 1200 EFF rows; 306 Stack Exchange test sentences)

| | shipped (`trim/none`) | chosen (`keep/0.10/space-only`) |
| :--- | ---: | ---: |
| rows leaking a passphrase word | 41 / 1200 | 16 / 1200 |
| passphrase words leaked | 105 / 5886 | 76 / 5886 |
| template words over-redacted | 528 | 549 |
| SE test sentences flagged (all false positives) | 0 | 0 |
| Oct 13 probe words leaked | 0 | 0 |
| golden / perturbed / write trace queries changed | - | 0 |
| `data/` identifiers newly flagged (of 51, x 6 cues) | - | 0 |

Leak causes: shipped no_flag_ops 6, other 7, stop_inside 3, tail_trim 25; chosen no_flag_ops 6, other 7, stop_inside 3

By separator (leak words, shipped -> chosen): space 67 -> 38, hyphen 11 -> 11, dot 4 -> 4, underscore 23 -> 23

Checks: oct13_no_leak pass, repo_queries_unchanged pass, fp_budget pass, over_budget pass, no_new_identifier_flags pass, fewer_leaked_words pass

**Ships on.**

Rows the chosen arm still leaks (first few):

- no_flag_ops: `the deploy token elderly-service-semantic-clean-livable-headphone stopped working, who rotates it?` leaks elderly, service, semantic, clean, livable, headphone
- other: `use Sprig Detonate Italicize Domestic Stallion Mammal 43 to log in to vault` leaks sprig, detonate, italicize, domestic, stallion, mammal
- stop_inside: `the deploy token Ungloved Energetic Broken Dowry Rudder 88 stopped working, who rotates it?` leaks ungloved, energetic, broken, dowry, rudder
- other: `use Dehydrate Lesser Flinch Numerator Underage Cahoots 67 to log in to vault` leaks dehydrate, lesser, flinch, numerator, underage, cahoots
- other: `The vault passphrase is had-financial-pouch-abide-ranch. Who owns vault-transit?` leaks financial, pouch, abide, ranch
- other: `use Basket Drift Other Backtalk Labored Headphone 47 to log in to vault` leaks basket, drift, other, backtalk, labored, headphone
