"""Pre-registered protocol for the Oct 31 passphrase knobs (committed before any scored run).

Questions:

* ``digit_guard``: with the guard, does the Oct 30 glued-digit knob keep its gain on
  Bitwarden-shape rows (one digit glued to one EFF word, ``Cascade5``) without newly
  flagging versioned names such as ``libgl1-mesa-dev``?
* ``plain_rule``: does asking a plain word to be a dictionary word (or a
  consonant-vowel invented word) cut the 221 of 1,867 Stack Exchange train
  identifiers the shipped detector flags, and what does it cost on passphrases made
  of invented words?

What was looked at before this file:

* the Oct 30 artifacts (the 12 SE train identifiers ``attached_digit`` newly flagged,
  ``artifacts/passphrase_digit_check.md``);
* on the SE *train* identifiers only (alphabetic set): a WordNet-noun version of
  ``plain_rule="dict"`` would leave 7 of the 221 shipped flags;
* scratch seeds 997 / 998 / 999 (600 rows each, never used below): Bitwarden-shape
  leaks 992 -> 11 words with the guard; the full-dictionary rule leaves 48 train
  identifier flags but leaks 635 of 2,979 invented-word passphrase words (21%),
  ``dict_cv`` 407 (14%); ``plain_scope="all"`` changed nothing there. That is why the
  invented-word budget below exists; it was set after seeing these numbers.

No seed below, no SE test sentence and no SE test identifier was scored by any arm
before this file was committed.

Grid: ``plain`` in {ops, dict/compounds, dict/all, dict_cv/compounds, dict_cv/all}
x ``digit`` in {off, raw (Oct 30 knob), guard} = 15 arms. (ops, off) is shipped.
Every other knob is pinned to the shipped value.

Calibration (``CALIB_*`` seeds, ``N_ROWS`` rows each; SE train sentences after either
cue regex, and SE train identifiers, alphabetic plus glued-digit, as in
``passphrase_digit_protocol.se_material``). An arm is *safe* when

1. no Oct 13 probe word leaks;
2. no golden / perturbed / phrasal-write trace ``query`` changes;
3. no ``data/`` identifier is newly flagged;
4. at most ``FP_BUDGET_TRAIN`` more SE train sentences are flagged;
5. at most ``IDENT_BUDGET_TRAIN`` SE train identifiers are *newly* flagged;
6. on each probe it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row;
7. on Oct 29-shape rows it leaks no more words than shipped;
8. on invented-word rows it leaks at most ``INVENTED_BUDGET`` (a share of the
   invented words) more than shipped. A secret that leaks is worse than a name that
   is over-redacted, so this budget is tight.

Pick: the safe arm with the fewest leaked words over the three probes; ties go to fewer
SE train identifiers flagged (absolute), then fewer SE train sentences flagged, then
fewer over-redacted words, then grid order.

One-shot confirm (``CONFIRM_*`` seeds, SE test). The pick ships on only if checks 1-8
hold with the test budgets (``FP_BUDGET_TEST``, ``IDENT_BUDGET_TEST``) and it either
leaks strictly fewer words than shipped, or leaks no more and flags strictly fewer SE
test identifiers. Otherwise it ships off; the confirm seeds are spent either way.

Reported, not gating: the shipped and picked arms on ``OFFLIST_SEED`` rows built from
the off-list control words.
"""

from __future__ import annotations

from typing import Any

CALIB_STANDARD_SEED = 3109
CALIB_ATTACHED_SEED = 3119
CALIB_INVENTED_SEED = 3121
CONFIRM_STANDARD_SEED = 3137
CONFIRM_ATTACHED_SEED = 3163
CONFIRM_INVENTED_SEED = 3167
OFFLIST_SEED = 3181
N_ROWS = 1200
FP_BUDGET_TRAIN = 15
FP_BUDGET_TEST = 1
IDENT_BUDGET_TRAIN = 9
IDENT_BUDGET_TEST = 1
OVER_BUDGET_PER_ROW = 0.5
INVENTED_BUDGET = 0.005
PLAIN = (("ops", "compounds"), ("dict", "compounds"), ("dict", "all"), ("dict_cv", "compounds"), ("dict_cv", "all"))
DIGIT = ("off", "raw", "guard")
SHIPPED = (("ops", "compounds"), "off")
PROBES = ("standard", "attached", "invented")


def arms() -> list[tuple[tuple[str, str], str]]:
    return [(p, d) for p in PLAIN for d in DIGIT]


def arm_name(arm: tuple) -> str:
    (rule, scope), digit = arm
    return f"{rule}/{scope}/{digit}"


def detector(arm: tuple):
    """Arms pin every knob, so a later change of the module defaults never moves them."""
    from ops_copilot.passphrase import CuedPassphraseDetector

    (rule, scope), digit = arm
    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True,
        attached_digit=digit != "off", digit_guard=digit == "guard",
        plain_rule=rule, plain_scope=scope,
    )


def patterns_for(arm: tuple):
    from ops_copilot import passphrase_compound_protocol as C

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def probe_rows(kind: str, seed: int, n: int = N_ROWS):
    from ops_copilot.passphrase_wordlist import invented_passphrases, wordlist_passphrases

    if kind == "standard":
        return wordlist_passphrases(seed, n)
    if kind == "attached":
        return wordlist_passphrases(seed, n, number_style="attached")
    if kind == "invented":
        return invented_passphrases(seed, n)
    raise ValueError(kind)


def calib_seeds() -> dict[str, int]:
    return {"standard": CALIB_STANDARD_SEED, "attached": CALIB_ATTACHED_SEED, "invented": CALIB_INVENTED_SEED}


def confirm_seeds() -> dict[str, int]:
    return {"standard": CONFIRM_STANDARD_SEED, "attached": CONFIRM_ATTACHED_SEED, "invented": CONFIRM_INVENTED_SEED}


def leak_total(res: dict) -> int:
    return sum(res["probe"][k]["total"]["leak_words"] for k in PROBES)


def is_safe(res: dict, base: dict, *, fp_budget: int, ident_budget: int) -> dict[str, bool]:
    out = {
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "data_idents": not res["data_ident_new_flags"],
        "se_sentences": res["se"]["sent_flagged"] - base["se"]["sent_flagged"] <= fp_budget,
        "se_identifiers": res["se"]["ident_new"] <= ident_budget,
        "standard_no_more_leaks": res["probe"]["standard"]["total"]["leak_words"] <= base["probe"]["standard"]["total"]["leak_words"],
        "invented_budget": res["probe"]["invented"]["total"]["leak_words"] - base["probe"]["invented"]["total"]["leak_words"]
        <= INVENTED_BUDGET * base["probe"]["invented"]["total"]["words"],
    }
    out["over_budget"] = all(
        res["probe"][k]["total"]["over_words"] - base["probe"][k]["total"]["over_words"] <= OVER_BUDGET_PER_ROW * base["probe"][k]["total"]["rows"]
        for k in PROBES
    )
    return out


def pick(results: list[dict], base: dict) -> dict | None:
    safe = [r for r in results if all(is_safe(r, base, fp_budget=FP_BUDGET_TRAIN, ident_budget=IDENT_BUDGET_TRAIN).values())]
    if not safe:
        return None
    order = {arm_name(a): i for i, a in enumerate(arms())}
    return min(safe, key=lambda r: (
        leak_total(r), r["se"]["ident_flagged"], r["se"]["sent_flagged"],
        sum(r["probe"][k]["total"]["over_words"] for k in PROBES), order[r["arm"]],
    ))


def confirm_passes(res: dict, base: dict) -> dict[str, Any]:
    chk = is_safe(res, base, fp_budget=FP_BUDGET_TEST, ident_budget=IDENT_BUDGET_TEST)
    fewer = leak_total(res) < leak_total(base)
    tie_fewer_ids = leak_total(res) <= leak_total(base) and res["se"]["ident_flagged"] < base["se"]["ident_flagged"]
    chk["gain"] = fewer or tie_fewer_ids
    return chk
