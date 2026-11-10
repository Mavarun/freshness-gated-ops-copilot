"""Pre-registered protocol for evidence-side compound parts (frozen 2026-11-10).

Written before the calibration grid was run and before any dev9 row or confirm swap was
scored. Disclosure, in full: the knob was motivated by the Nov 9 post-hoc reading
(``artifacts/nonkey_posthoc.md``: 2 of 5 rows ``all`` lost miss a word that is a hyphen
part of a cited token, ``checkout`` in ``checkout-primary``). While writing the knob's
unit tests, three spot queries were run: dev8 row d8-06 under ``all`` with and without
parts, and the Nov 9 AppRole ``token`` swap. The swap exposed that synonym alts of a part
let ``token`` ride on ``platform-secrets``; parts were restricted to the word itself
before anything else was run. dev9 was written and committed before the knob existed.

Calibration: golden (51) + dev2-dev6 (221) + dev8 (48, spent on Nov 9 and now
calibration data: its 32 wordy rows are ANSWER rows and its 16 topic traps must-refuse
rows), and the *same* 384 swaps as the Nov 7 and Nov 9 protocols (built on golden +
dev2-dev6 only, ``CAL_DRAWS`` per term, seed ``CAL_SEED``), so the numbers line up.

Eligible arm: loses at most ``MAX_LOST_CAL`` calibration ANSWER rows against the shipped
default and opens no more must-refuse rows than it. Pick: lowest swap pass rate; ties go
to fewer lost rows, then the earlier arm. Nothing is picked unless the pass rate drops by
at least ``MIN_DROP``. The Nov 9 ``all`` arm is scored as a reference and cannot be picked
(it already failed its confirm).

Confirm, once: rows = dev9 wordy (32, new) + dev7 + synonym_fresh + the 203-row
robustness set; swaps built on them by the shipped default with ``CONFIRM_DRAWS`` per term
and a new seed ``CONFIRM_SEED``; traps = the 114 attribute traps (v1-v3) and the 16 dev9
topic traps. The picked arm ships on only if, against the shipped default on the same
swaps, its pass rate drops by at least ``MIN_DROP`` absolute and ``MIN_REL_DROP``
relative, it loses at most ``MAX_LOST_CONFIRM`` confirm ANSWER rows (dev9 wordy rows
included), opens no attribute trap and opens no more dev9 topic traps than the shipped
default. Known caveat: dev7, fresh and the 203-row set were confirm rows on Nov 9 too
(new swap seed, same rows); only dev9 is unseen.
"""

from __future__ import annotations

from ops_copilot import nonkey_coverage_protocol as _nov9

ARMS: dict[str, dict] = {
    "shipped": {},
    "all": {"grounding_nonkey_rule": "all"},
    "all_hyphen": {"grounding_nonkey_rule": "all", "grounding_nonkey_parts": "hyphen"},
    "all_joined": {"grounding_nonkey_rule": "all", "grounding_nonkey_parts": "joined"},
    "corpus_hyphen": {"grounding_nonkey_rule": "corpus", "grounding_nonkey_parts": "hyphen"},
}
REFERENCE_ONLY = ("all",)
DEV8_FILE = _nov9.DEV8_FILE
DEV9_FILE = "data/eval/nonkey_dev9.jsonl"
CAL_FILES = (*_nov9.CAL_FILES, DEV8_FILE)
SWAP_BASE_FILES = _nov9.CAL_FILES
CONFIRM_FILES = (DEV9_FILE, "data/eval/synonym_dev7.jsonl", "data/eval/synonym_fresh.jsonl")
TRAP_FILES = _nov9.TRAP_FILES
CAL_DRAWS = _nov9.CAL_DRAWS
CAL_SEED = _nov9.CAL_SEED
CONFIRM_DRAWS = 3
CONFIRM_SEED = 1110
MAX_LOST_CAL = 2
MIN_DROP = 0.03
MIN_REL_DROP = 0.25
MAX_LOST_CONFIRM = 2


def lost(arm: dict, ref: dict) -> int:
    return ref["answered"] - arm["answered"]


def eligible(arm: dict, ref: dict) -> bool:
    return lost(arm, ref) <= MAX_LOST_CAL and arm["refuse_opened"] <= ref["refuse_opened"]


def pick(scores: dict[str, dict]) -> str | None:
    """Arm picked from ``{arm: NullScore.as_dict()}``; None when nothing clears ``MIN_DROP``."""
    ref = scores["shipped"]
    ref_rate = ref["rates"]["null_pass_rate"]
    best, best_key = None, None
    for i, name in enumerate(ARMS):
        if name == "shipped" or name in REFERENCE_ONLY or name not in scores:
            continue
        if not eligible(scores[name], ref):
            continue
        rate = scores[name]["rates"]["null_pass_rate"]
        if ref_rate - rate < MIN_DROP:
            continue
        key = (rate, lost(scores[name], ref), i)
        if best_key is None or key < best_key:
            best, best_key = name, key
    return best


def ships(arm: dict, ref: dict, attr_opens: int, topic_opens: int, ref_topic_opens: int) -> bool:
    a, r = arm["rates"]["null_pass_rate"], ref["rates"]["null_pass_rate"]
    drop = r - a
    return (
        drop >= MIN_DROP
        and (r > 0 and drop / r >= MIN_REL_DROP)
        and lost(arm, ref) <= MAX_LOST_CONFIRM
        and attr_opens == 0
        and topic_opens <= ref_topic_opens
    )
