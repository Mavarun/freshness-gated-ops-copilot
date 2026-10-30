"""Pre-registered protocol for the Oct 30 passphrase knobs (committed before any scored run).

Question: do the off-by-default EFF-list membership arm (``wordlist_compounds`` /
``wordlist_space``), with the exact ``data/`` exemption list on, and the
trailing-number purpose pattern (``explain_redact.LOGIN_SECRET_NUM_RE``) cut the
passphrase words the shipped detector leaks, without flagging real identifiers
or prose?

What was looked at before this file:

* the spent Oct 29 seeds (2910, 2929, 2931) with the shipped detector only: on
  2931 the leaks are 6 ``no_flag_ops`` rows (ops-word compounds), 7 ``other``
  (mostly six-word Title-Case passphrases in the purpose template) and 3
  ``stop_inside``;
* scratch seed 999 (900 compound rows; 26 not flagged by the ops-word count) and
  the Stack Exchange *train* identifiers: of the 1,646 3+ part train names the
  count rule does not flag, 28 have every part on the EFF list, 0 of the 285 with
  four or more parts do; the pair-cosine arm at 0.05 would flag 233 of them, so it
  is not in this grid;
* the size of the Stack Exchange *test* identifier set, nothing else about it.

Neither seed below, and no Stack Exchange test sentence or test identifier, was
scored by any arm before this file was committed.

Grid: ``compound`` in {None, all4, but1_4, all3} x ``space`` in {off, on} x
``purpose_number`` in {off, on} = 16 arms. The exact exemption list is on
whenever the compound arm is. (None, off, off) is the shipped detector.

Calibration (``CALIB_SEED``, ``N_ROWS`` rows; Stack Exchange train). An arm is
*safe* when

1. no word of the Oct 13 synthetic probe leaks;
2. no trace ``query`` of the golden, perturbed and phrasal-write rows changes
   versus the shipped patterns;
3. it flags at most ``FP_BUDGET_TRAIN`` more Stack Exchange train sentences than
   the shipped detector (the Oct 29 budget);
4. it newly flags at most ``IDENT_BUDGET_TRAIN`` Stack Exchange train identifiers
   (0.5% of the train set);
5. it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row;
6. it flags no ``data/`` identifier that the shipped detector does not.

Pick: the safe arm with the fewest leaked words; ties go to fewer over-redacted
words, then grid order (fewer knobs first).

One-shot confirm (``CONFIRM_SEED``, Stack Exchange test). The pick ships on only
if it leaks strictly fewer words than the shipped patterns on the confirm rows,
checks 1, 2, 5 and 6 hold, it flags at most ``FP_BUDGET_TEST`` more test
sentences and newly flags at most ``IDENT_BUDGET_TEST`` test identifiers.
Otherwise it ships off; the confirm seed is spent either way.

Reported, not gating: the same scores on ``OFFLIST_SEED`` rows built from the
off-list control words (``passphrase_wordlist.offlist_words``). The membership
arm should gain close to nothing there; a large gain would mean the arm fires on
something other than list membership.
"""

from __future__ import annotations

from typing import Any

CALIB_SEED = 3010
CONFIRM_SEED = 3037
OFFLIST_SEED = 3053
N_ROWS = 1200
COMPOUND_MODES = (None, "all4", "but1_4", "all3")
FP_BUDGET_TRAIN = 15
FP_BUDGET_TEST = 1
IDENT_BUDGET_TRAIN = 9
IDENT_BUDGET_TEST = 1
OVER_BUDGET_PER_ROW = 0.5
SHIPPED = (None, False, False)


def arms() -> list[tuple[str | None, bool, bool]]:
    return [(c, sp, pn) for c in COMPOUND_MODES for sp in (False, True) for pn in (False, True)]


def arm_name(arm: tuple) -> str:
    c, sp, pn = arm
    return f"{c or 'none'}/{'space' if sp else '-'}/{'num' if pn else '-'}"


def detector(arm: tuple):
    """Arms pin every knob, so a later change of the module defaults never moves them."""
    from ops_copilot.passphrase import CuedPassphraseDetector

    c, sp, _ = arm
    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds=c, wordlist_space=sp, exempt_identifiers=c is not None,
    )


def patterns_for(arm: tuple):
    from ops_copilot.explain_redact import LOGIN_SECRET_NUM_RE, LOGIN_SECRET_RE, SENSITIVE_PATTERNS

    det = detector(arm)
    out = []
    for k, p in SENSITIVE_PATTERNS:
        if k == "passphrase":
            p = det
        elif p is LOGIN_SECRET_RE or p is LOGIN_SECRET_NUM_RE:
            p = LOGIN_SECRET_NUM_RE if arm[2] else LOGIN_SECRET_RE
        out.append((k, p))
    return tuple(out)


def data_identifier_new_flags(arm: tuple) -> list[str]:
    from ops_copilot import passphrase_tail_protocol as T

    det, base = detector(arm), detector(SHIPPED)
    return [
        f"{c} {n}" for n in T.data_identifiers() for c in T.IDENTIFIER_CUES
        if det.search(f"{c} {n}") and not base.search(f"{c} {n}")
    ]


def shipped_repo_queries() -> dict[str, str]:
    from ops_copilot import passphrase_tail_protocol as T
    from ops_copilot.passphrase_wordlist import redact_query

    pats = patterns_for(SHIPPED)
    return {q: redact_query(q, pats) for q in dict.fromkeys(T.repo_queries())}


def evaluate_arm(arm, rows, se_sentences, se_idents, *, base_queries, base_ident_flags) -> dict[str, Any]:
    from ops_copilot import passphrase_tail_protocol as T
    from ops_copilot.passphrase_identifiers import score_identifiers
    from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows

    pats = patterns_for(arm)
    det = detector(arm)
    return {
        "arm": arm_name(arm),
        "probe": score_rows(rows, pats),
        "oct13_leak_words": sum(sum(_present(redact_query(t, pats).lower(), w) for w in ws) for t, ws in T.oct13_probe_texts()),
        "repo_query_changes": sum(redact_query(q, pats) != red for q, red in base_queries.items()),
        "se": T.se_flags(det, se_sentences),
        "idents": score_identifiers(det, se_idents, base=base_ident_flags),
        "data_ident_new_flags": data_identifier_new_flags(arm),
    }


def is_safe(res: dict, base: dict, *, fp_budget: int, ident_budget: int) -> dict[str, bool]:
    n = res["probe"]["total"]["rows"]
    return {
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "fp_budget": res["se"]["flagged"] - base["se"]["flagged"] <= fp_budget,
        "ident_budget": res["idents"]["new_flags"] <= ident_budget,
        "over_budget": res["probe"]["total"]["over_words"] - base["probe"]["total"]["over_words"] <= OVER_BUDGET_PER_ROW * n,
        "data_idents": not res["data_ident_new_flags"],
    }


def pick(results: list[dict], base: dict) -> dict | None:
    safe = [r for r in results if all(is_safe(r, base, fp_budget=FP_BUDGET_TRAIN, ident_budget=IDENT_BUDGET_TRAIN).values())]
    if not safe:
        return None
    order = {arm_name(a): i for i, a in enumerate(arms())}
    return min(safe, key=lambda r: (r["probe"]["total"]["leak_words"], r["probe"]["total"]["over_words"], order[r["arm"]]))


def confirm_passes(res: dict, base: dict) -> dict[str, bool]:
    chk = is_safe(res, base, fp_budget=FP_BUDGET_TEST, ident_budget=IDENT_BUDGET_TEST)
    chk["fewer_leaked_words"] = res["probe"]["total"]["leak_words"] < base["probe"]["total"]["leak_words"]
    return chk
