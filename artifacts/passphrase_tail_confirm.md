# Passphrase tail / incoherence arm: one-shot confirm (seed 2929, 1200 EFF rows; 306 Stack Exchange test sentences)

| | shipped (`trim/none`) | chosen (`keep/0.10`) |
| :--- | ---: | ---: |
| rows leaking a passphrase word | 32 / 1200 | 7 / 1200 |
| passphrase words leaked | 93 / 5978 | 41 / 5978 |
| template words over-redacted | 503 | 539 |
| SE test sentences flagged (all false positives) | 0 | 0 |
| Oct 13 probe words leaked | 0 | 0 |
| golden / perturbed / write trace queries changed | - | 0 |

Leak causes: shipped no_flag_ops 6, other 7, stop_inside 1, tail_trim 18; chosen other 6, stop_inside 1

By separator (leak words, shipped -> chosen): space 68 -> 41, hyphen 10 -> 0, dot 10 -> 0, underscore 5 -> 0

Checks: oct13_no_leak pass, repo_queries_unchanged pass, fp_budget pass, over_budget pass, fewer_leaked_words pass

**Ships on.**

Rows the chosen arm still leaks (first few):

- other: `use Decline Patrol Hurricane Numerous Quiver Culture 12 to log in to vault` leaks decline, patrol, hurricane, numerous, quiver, culture
- other: `use Underuse Cursive Neon Unlikable Stretch Backfield 28 to log in to vault` leaks underuse, cursive, neon, unlikable, stretch, backfield
- other: `use Width Overcook Amulet Stays Macaroni Tamale 27 to log in to vault` leaks width, overcook, amulet, stays, macaroni, tamale
- stop_inside: `the deploy token Vineyard From Bulldog Dial Freebase 23 stopped working, who rotates it?` leaks vineyard, from, bulldog, dial, freebase
- other: `use Denial Judgingly Wildlife Stylized Recede Absolute 15 to log in to vault` leaks denial, judgingly, wildlife, stylized, recede, absolute
- other: `use Unaudited Bartender Squealing Subsector Cosponsor Riveting 47 to log in to vault` leaks unaudited, bartender, squealing, subsector, cosponsor, riveting
