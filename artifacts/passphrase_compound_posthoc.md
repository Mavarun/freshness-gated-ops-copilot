# Oct 30 passphrase ship: post-hoc (after the confirm)

## Which knob does the work (leaked words of ~5,960 / 5,990)

| arm | confirm seed 3037 | off-list control 3053 |
| --- | ---: | ---: |
| none/-/- | 128 | 63 |
| none/-/num | 39 | 33 |
| none/space/- | 124 | 63 |
| none/space/num | 35 | 33 |
| all4/-/- | 109 | 63 |
| all4/-/num | 20 | 33 |
| all4/space/- | 105 | 63 |
| all4/space/num | 16 | 33 |

## Confirm rows still leaking under the shipped patterns (4)

- `the deploy token carrot many caravan failing possibly browbeat stopped working, who rotates it?` -> carrot, many, caravan, failing, possibly, browbeat
- `The vault passphrase is running.pagan.curing.unnoticed.character. Who owns vault-transit?` -> running, pagan, curing, unnoticed, character
- `my password is Panda Epilepsy Sleek Why Entrust Puritan 53, why can't I log in?` -> entrust, puritan
- `The vault passphrase is Had Antitrust Zap Nebulizer Confirm 42. Who owns vault-transit?` -> antitrust, nebulizer, confirm

## Bitwarden-style numbers (seed 3061, one digit glued to a random word)

Rows leaking: Oct 29 452 -> shipped 452 of 1,200; words leaked 1977 -> 1977 of 5,944.

| separator | rows leaking (shipped) | words leaked (shipped) |
| --- | ---: | ---: |
| space | 114 / 300 | 435 |
| hyphen | 121 / 300 | 607 |
| dot | 109 / 300 | 382 |
| underscore | 108 / 300 | 553 |

Examples (shipped):

- `the deploy token porous patronage cascade5 purveyor stopped working, who rotates it?`
- `log in to grafana with passphrase Drove.Dangle2.Unsubtle.Comprised please`
- `the deploy token nutmeg.margarita.tribesman.robust0.frighten stopped working, who rotates it?`
- `the deploy token Appetizer7_Trusting_Unpeeled_Extrude stopped working, who rotates it?`
- `the deploy token Lip-Smilingly-Igloo3-Bladder-Resurrect stopped working, who rotates it?`
