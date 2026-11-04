"""Pre-registered protocol for the Nov 4 ``space_bridge`` knob (committed before any scored run).

Question: the Nov 1 function-parts slice closed ``-`` / ``.`` / ``_`` compounds that hold a function
word (883 -> 19 leaked words on the confirm seeds) and left space-joined phrases alone: 468 of the
487 words still leaking on those seeds were in ``detergent in turtle clerk``-style phrases, because
a stop word ends a space run. Does letting a space run hold up to ``space_bridge_max`` function words
(``passphrase.bridge_words``) close that without new false flags on real Stack Exchange sentences?

What was looked at before this file:

* the Nov 1 confirm summary (phrase probe leaked words by separator, space 468 of 487);
* the Nov 4 detector on about a dozen hand-written strings, a few of them near copies of Nov 1 README
  examples (``log in with passphrase detergent in turtle clerk goofiness please``,
  ``the password is at the end of the line``...), to check the span ends and the prose cases.

No seed below, no SE sentence and no SE identifier was scored by the knob before this file was
committed. Design caveats, fixed now: (1) ``PHRASE_WORDS`` (the phrase probe's function words) is a
subset of ``FUNCTION_WORDS`` but not of ``PREP_WORDS``, so the probe favours the ``func`` and ``stop``
arms over ``prep``; (2) a bridge word may not be first, last or follow another bridge word, so
``in the`` in a row still ends a run; (3) the SE sentence sets are the control for false flags, and
the ``connective`` probe (14 connectives on no list, ``passphrase_wordlist.CONNECTIVE_WORDS``) is the
control for generalisation past a list. It is reported and held to the no-extra-leak checks, but a
gain on it is not required.

Arms ``(bridge list, max bridge words)``: ``(None, 0)`` = shipped Nov 1 detector, ``(prep, 1)``,
``(prep, 2)``, ``(func, 2)``, ``(stop, 2)``. Every other knob is pinned to the Nov 1 shipped value.

Calibration (``CALIB_SEEDS``, six probes x ``N_ROWS``, SE *train*). An arm is *safe* when

1. no Oct 13 probe word leaks;
2. no golden / perturbed / phrasal-write trace ``query`` changes;
3. no ``data/`` identifier is newly flagged;
4. at most ``SENT_BUDGET_TRAIN`` more SE train sentences are flagged;
5. at most ``IDENT_BUDGET_TRAIN`` SE train identifiers are newly flagged;
6. on each probe it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row;
7. on no probe does it leak more words than shipped;

and *gains* when it leaks strictly fewer phrase-probe words. Pick: the safe arm with a gain that leaks
the fewest phrase words; ties go to grid order (smaller list, fewer bridge words first).

One-shot confirm (``CONFIRM_SEEDS``, SE *test*): the pick ships on only if checks 1-7 hold with the
test budgets (``SENT_BUDGET_TEST``, ``IDENT_BUDGET_TEST``) and the gain holds. If no arm is safe with a
gain, the knob stays off and the confirm seeds stay unspent.
"""

from __future__ import annotations

from typing import Any

CALIB_SEEDS = {"standard": 3407, "attached": 3413, "invented": 3419, "cased": 3423, "phrase": 3401, "connective": 3427}
CONFIRM_SEEDS = {"standard": 3433, "attached": 3439, "invented": 3449, "cased": 3457, "phrase": 3461, "connective": 3463}
N_ROWS = 1200
OVER_BUDGET_PER_ROW = 0.5
SENT_BUDGET_TRAIN = 5
SENT_BUDGET_TEST = 1
IDENT_BUDGET_TRAIN = 3
IDENT_BUDGET_TEST = 1
PROBES = ("standard", "attached", "invented", "cased", "phrase", "connective")
SHIPPED: tuple[str | None, int] = (None, 0)  # the Nov 1 detector (function_parts on, no space bridge)
GRID: tuple[tuple[str | None, int], ...] = (SHIPPED, ("prep", 1), ("prep", 2), ("func", 2), ("stop", 2))


def arms() -> list[tuple[str | None, int]]:
    return list(GRID)


def arm_name(arm: tuple[str | None, int]) -> str:
    return "shipped" if arm[0] is None else f"{arm[0]}/{arm[1]}"


def detector(arm: tuple[str | None, int]):
    """Pins every knob to the Nov 1 shipped value, so later default changes never move it."""
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True,
        attached_digit=True, digit_guard=True, plain_rule="ops", plain_scope="compounds",
        shape_guards=("case", "tld"), function_parts=True,
        space_bridge=arm[0], space_bridge_max=arm[1],
    )


def patterns_for(arm: tuple[str | None, int]):
    from ops_copilot import passphrase_compound_protocol as C

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def probe_rows(kind: str, seed: int, n: int = N_ROWS):
    if kind == "connective":
        from ops_copilot.passphrase_wordlist import connective_passphrases

        return connective_passphrases(seed, n)
    from ops_copilot.passphrase_shape_protocol import probe_rows as rows

    return rows(kind, seed, n)


def checks(res: dict, base: dict, *, sent_budget: int, ident_budget: int) -> dict[str, Any]:
    p, b = res["probe"], base["probe"]
    return {
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "data_idents": not res["data_ident_new_flags"],
        "se_sentences": res["se"]["sent_flagged"] - base["se"]["sent_flagged"] <= sent_budget,
        "se_identifiers": res["se"]["ident_new"] <= ident_budget,
        "over_budget": all(
            p[k]["total"]["over_words"] - b[k]["total"]["over_words"] <= OVER_BUDGET_PER_ROW * b[k]["total"]["rows"]
            for k in PROBES
        ),
        "no_more_leaks": all(p[k]["total"]["leak_words"] <= b[k]["total"]["leak_words"] for k in PROBES),
        "gain": p["phrase"]["total"]["leak_words"] < b["phrase"]["total"]["leak_words"],
    }


def calibration_passes(res: dict, base: dict) -> dict[str, Any]:
    return checks(res, base, sent_budget=SENT_BUDGET_TRAIN, ident_budget=IDENT_BUDGET_TRAIN)


def confirm_passes(res: dict, base: dict) -> dict[str, Any]:
    return checks(res, base, sent_budget=SENT_BUDGET_TEST, ident_budget=IDENT_BUDGET_TEST)


def pick(results: list[dict], base: dict) -> dict | None:
    """The safe arm with a gain and the fewest phrase-probe leaked words; ties go to grid order."""
    order = {arm_name(a): i for i, a in enumerate(arms())}
    ok = [r for r in results if r["arm"] != arm_name(SHIPPED) and all(calibration_passes(r, base).values())]
    if not ok:
        return None
    return min(ok, key=lambda r: (r["probe"]["phrase"]["total"]["leak_words"], order[r["arm"]]))
