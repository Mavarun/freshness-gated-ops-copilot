"""Second pre-registered space-bridge protocol (Nov 4, committed before any scored run).

The first protocol (``passphrase_space_protocol``) found no safe arm: the best gain, phrase-probe leaked
words 468 -> 94 with the ``func`` list, came with 28-56 new SE *train* sentence flags (budget 5), and
``artifacts/passphrase_space_calibration.md`` says so. Its confirm seeds were never spent.

What was looked at before this file (and so is *design data*, not evidence):

* the 28 / 36 / 47 / 56 new SE train sentence flags of the four arms (``scripts/diagnose_space_bridge.py``).
  Every one holds at least one content word that is off the EFF list (``managers``, ``outcomes``,
  ``instances``). That is where the rule below comes from, so zero new SE *train* flags for an
  ``eff`` arm is true by construction and proves nothing; the SE *test* split and the controls are the evidence;
* the v1 calibration probe numbers (phrase 468 -> 207 with ``prep``, 94 with ``func``; connective 135, unchanged).

No seed below and no SE test sentence was scored with ``space_bridge_rule`` before this file. The rule
(``passphrase.CuedPassphraseDetector._bridge_eff_span``): a bridged space run is read only when every
content word is on the EFF list, there are 3 (``eff3``) or 4 (``eff4``) of them and at least one bridge
word sits inside the run; the run is cut at the first off-list word. Costs known in advance and measured by
two controls: (1) a passphrase made of words *off* the EFF list gets nothing (``offlist_phrase`` probe,
reported, a gain is neither expected nor required); (2) real prose that happens to use only list words
after a credential noun is flagged (the SE sentence budget measures it). The ``phrase`` probe draws from
the EFF list, so it overstates the gain on real phrases; ``connective`` words are on no bridge list, so
no arm should gain there.

Arms ``(bridge list, max bridge words, rule)``: shipped (Nov 1 detector), ``prep/2/eff3``, ``prep/2/eff4``,
``func/2/eff3``, ``func/2/eff4``. Every other knob is pinned to the Nov 1 shipped value.

Calibration (``CALIB_SEEDS``, seven probes x ``N_ROWS``, SE *train*): the checks of the first protocol
(1-7 there, the probe list here has seven entries). The pick is the safe arm with a gain that leaks the
fewest phrase words; ties go to grid order. One-shot confirm (``CONFIRM_SEEDS``, SE *test*) with the test
budgets; it ships on only if every check holds. No safe arm with a gain: the knob stays off and the
confirm seeds stay unspent.
"""

from __future__ import annotations

from typing import Any

from ops_copilot import passphrase_space_protocol as V1

Arm = tuple[str | None, int, str]
CALIB_SEEDS = {"standard": 3507, "attached": 3513, "invented": 3519, "cased": 3523, "phrase": 3501,
               "connective": 3527, "offlist_phrase": 3529}
CONFIRM_SEEDS = {"standard": 3533, "attached": 3539, "invented": 3549, "cased": 3557, "phrase": 3561,
                 "connective": 3563, "offlist_phrase": 3567}
N_ROWS = V1.N_ROWS
SENT_BUDGET_TRAIN, SENT_BUDGET_TEST = V1.SENT_BUDGET_TRAIN, V1.SENT_BUDGET_TEST
IDENT_BUDGET_TRAIN, IDENT_BUDGET_TEST = V1.IDENT_BUDGET_TRAIN, V1.IDENT_BUDGET_TEST
OVER_BUDGET_PER_ROW = V1.OVER_BUDGET_PER_ROW
PROBES = ("standard", "attached", "invented", "cased", "phrase", "connective", "offlist_phrase")
SHIPPED: Arm = (None, 0, "plain")
GRID: tuple[Arm, ...] = (SHIPPED, ("prep", 2, "eff3"), ("prep", 2, "eff4"), ("func", 2, "eff3"), ("func", 2, "eff4"))


def arms() -> list[Arm]:
    return list(GRID)


def arm_name(arm: Arm) -> str:
    return "shipped" if arm[0] is None else f"{arm[0]}/{arm[1]}/{arm[2]}"


def detector(arm: Arm):
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True,
        attached_digit=True, digit_guard=True, plain_rule="ops", plain_scope="compounds",
        shape_guards=("case", "tld"), function_parts=True,
        space_bridge=arm[0], space_bridge_max=arm[1], space_bridge_rule=arm[2],
    )


def patterns_for(arm: Arm):
    from ops_copilot import passphrase_compound_protocol as C

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def probe_rows(kind: str, seed: int, n: int = N_ROWS):
    if kind == "offlist_phrase":
        from ops_copilot.passphrase_wordlist import offlist_phrase_passphrases

        return offlist_phrase_passphrases(seed, n)
    return V1.probe_rows(kind, seed, n)


def calibration_passes(res: dict, base: dict) -> dict[str, Any]:
    return V1.checks(res, base, sent_budget=SENT_BUDGET_TRAIN, ident_budget=IDENT_BUDGET_TRAIN, probes=PROBES)


def confirm_passes(res: dict, base: dict) -> dict[str, Any]:
    return V1.checks(res, base, sent_budget=SENT_BUDGET_TEST, ident_budget=IDENT_BUDGET_TEST, probes=PROBES)


def pick(results: list[dict], base: dict) -> dict | None:
    order = {arm_name(a): i for i, a in enumerate(arms())}
    ok = [r for r in results if r["arm"] != arm_name(SHIPPED) and all(calibration_passes(r, base).values())]
    if not ok:
        return None
    return min(ok, key=lambda r: (r["probe"]["phrase"]["total"]["leak_words"], order[r["arm"]]))
