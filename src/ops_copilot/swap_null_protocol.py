"""Pre-registered protocol for closing random-word passage rescues (frozen 2026-11-07).

Written before the calibration grid was run through this module and before any confirm
*swap* was scored. Disclosure, in full: while exploring, ad-hoc scripts ran the shipped
default, ``known_off``, ``sense_all`` and two credited-rank variants on the golden set
and dev2-dev6 with one random swap per term (seed 1107; shipped 42 of 128 swaps answered,
30 through a passage rescue), and also counted, per arm, the dev7 + fresh ANSWER rows
kept (4 / 3 / 1 / 1 / 1), the 203-row robustness accuracy (171 / 169 / 168 / 168 / 168)
and attribute-trap opens (0 of 114 for all). ``sense_known`` was not run on any of them.
No swap on a confirm row has been scored.

Calibration rows: golden (51) + dev2-dev6 (221). Swaps: ``CAL_DRAWS`` random corpus
words per salient term of every row the shipped default answers, seed ``CAL_SEED``.

Eligible arm: loses at most ``MAX_LOST_CAL`` calibration ANSWER rows relative to the
shipped default and opens no more must-refuse rows than it.
Pick: the eligible arm with the lowest swap pass rate; ties go to fewer lost rows, then
to the earlier arm. Nothing is picked unless the pass rate drops by at least
``MIN_DROP`` (absolute) relative to the shipped default.

Confirm, once: rows = dev7 + synonym_fresh + the 203-row robustness set; swaps built on
them with ``CONFIRM_DRAWS`` per term and a new seed ``CONFIRM_SEED``; plus the 114
attribute traps (v1-v3). The picked arm ships on only if, against the shipped default on
the same swaps, its pass rate drops by at least ``MIN_DROP`` absolute and
``MIN_REL_DROP`` relative, it loses at most ``MAX_LOST_CONFIRM`` confirm ANSWER rows and
opens no attribute trap. Otherwise it ships off.
"""

from __future__ import annotations

ARMS: dict[str, dict] = {
    "shipped": {},
    "known_off": {"passage_support_known_words": False},
    "sense_all": {"passage_support_sense_check": True},
    "sense_known": {"passage_support_known_sense_check": True},
    "credit_rank5": {"passage_support_credit_max_rank": 5},
}
CAL_FILES = tuple(f"data/eval/synonym_dev{i}.jsonl" for i in range(2, 7))
CONFIRM_FILES = ("data/eval/synonym_dev7.jsonl", "data/eval/synonym_fresh.jsonl")
TRAP_FILES = tuple(f"data/eval/{n}.jsonl" for n in ("attribute_traps", "attribute_traps_v2", "attribute_traps_v3"))
CAL_DRAWS = 3
CAL_SEED = 1107
CONFIRM_DRAWS = 3
CONFIRM_SEED = 2611
MAX_LOST_CAL = 2
MIN_DROP = 0.05
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
        if name == "shipped" or name not in scores or not eligible(scores[name], ref):
            continue
        rate = scores[name]["rates"]["null_pass_rate"]
        if ref_rate - rate < MIN_DROP:
            continue
        key = (rate, lost(scores[name], ref), i)
        if best_key is None or key < best_key:
            best, best_key = name, key
    return best


def ships(arm: dict, ref: dict, trap_opens: int) -> bool:
    a, r = arm["rates"]["null_pass_rate"], ref["rates"]["null_pass_rate"]
    drop = r - a
    return (
        drop >= MIN_DROP
        and (r > 0 and drop / r >= MIN_REL_DROP)
        and lost(arm, ref) <= MAX_LOST_CONFIRM
        and trap_opens == 0
    )
