"""Pre-registered protocol for the Nov 1 ``function_parts`` knob (committed before any scored run).

Question: the shape-guard protocol's new phrase probe showed the shipped detector
leaking about a quarter of the words of passphrases that hold a function word
(``turtle_unproven_in_spider_sampling_slug``). Does reading up to two function-word
parts inside a ``-`` / ``.`` / ``_`` compound (``passphrase.function_parts``) close
that on compounds without new false flags on real Stack Exchange text?

What was looked at before this file:

* the spent shape-guard calibration seed 3229 (phrase probe): leak causes for the
  shipped detector (other 279, tail_trim 74, no_flag_ops 16 rows), leaks by
  separator (space 372, hyphen 316, underscore 334, dot 230 words) and its first
  eight leaking rows, which is how the two-letter-part cause was found;
* eight hand-written strings (four leaking rows above, ``chicken-and-egg``,
  ``name-for-all-parts``, ``all-in-one-solution``, ``ab-cd-ef-gh``) with the knob on.

No seed below, no SE sentence and no SE identifier was scored with the knob before
this file was committed. The function-word list (``passphrase.FUNCTION_WORDS``)
contains every word the phrase probe inserts (``passphrase_wordlist.PHRASE_WORDS``),
so the phrase probe overstates recall on real phrases; the SE sets are the control.
Space-joined phrases (a stop word ends the run) are out of scope; their leaks are
expected to stay.

Arms: ``False`` (shipped Nov 1 detector, shape guards ``case`` + ``tld`` on) and
``True``. Every other knob is pinned.

Calibration (``CALIB_SEEDS``, five probes x ``N_ROWS``, SE *train*). The knob is
*safe* when

1. no Oct 13 probe word leaks;
2. no golden / perturbed / phrasal-write trace ``query`` changes;
3. no ``data/`` identifier is newly flagged;
4. at most ``SENT_BUDGET_TRAIN`` more SE train sentences are flagged;
5. at most ``IDENT_BUDGET_TRAIN`` SE train identifiers are newly flagged;
6. on each probe it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row;
7. on no probe does it leak more words than shipped;

and it has a *gain*: strictly fewer leaked phrase-probe words. If the knob is safe
with a gain it goes to the one-shot confirm (``CONFIRM_SEEDS``, SE *test*), where
it ships on only if checks 1-7 hold with the test budgets (``SENT_BUDGET_TEST``,
``IDENT_BUDGET_TEST``) and the gain holds. The confirm seeds are spent either way.
"""

from __future__ import annotations

from typing import Any

CALIB_SEEDS = {"standard": 3307, "attached": 3313, "invented": 3319, "cased": 3323, "phrase": 3301}
CONFIRM_SEEDS = {"standard": 3329, "attached": 3331, "invented": 3343, "cased": 3347, "phrase": 3359}
N_ROWS = 1200
OVER_BUDGET_PER_ROW = 0.5
SENT_BUDGET_TRAIN = 5
SENT_BUDGET_TEST = 1
IDENT_BUDGET_TRAIN = 3
IDENT_BUDGET_TEST = 1
SHIPPED = False
PROBES = ("standard", "attached", "invented", "cased", "phrase")


def arms() -> list[bool]:
    return [False, True]


def arm_name(arm: bool) -> str:
    return "function_parts" if arm else "shipped"


def detector(arm: bool):
    """Pins every knob to the Nov 1 shipped value, so later default changes never move it."""
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True,
        attached_digit=True, digit_guard=True, plain_rule="ops", plain_scope="compounds",
        shape_guards=("case", "tld"), function_parts=bool(arm),
    )


def patterns_for(arm: bool):
    from ops_copilot import passphrase_compound_protocol as C

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def probe_rows(kind: str, seed: int, n: int = N_ROWS):
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
