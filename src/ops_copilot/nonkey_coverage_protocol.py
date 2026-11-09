"""Pre-registered protocol for the non-key coverage rule (frozen 2026-11-09).

Written before the calibration grid was run and before any dev8 row or confirm swap was
scored. Disclosure, in full: the arms were designed after reading the 42 calibration swaps
the shipped default still answers (``artifacts/swap_null_report.json``: 25 have the
swapped word outside the key half with nothing supporting it). While writing the knob and
its unit tests, four spot queries were run under each rule: the AppRole ``token`` swap,
the original AppRole question, the primary on-call question and the checkout_retry
``memory`` swap. Nothing else was run.

Calibration: golden (51) + dev2-dev6 (221) rows, and the *same* 384 swaps the Nov 7
protocol and the CI gate use (``CAL_DRAWS`` per term, seed ``CAL_SEED``, drawn on the rows
the pre-Nov-7 default answered), so the 42-swap residual is the baseline.

Eligible arm: loses at most ``MAX_LOST_CAL`` calibration ANSWER rows relative to the
shipped default and opens no more must-refuse rows than it.
Pick: the eligible arm with the lowest swap pass rate; ties go to fewer lost rows, then
the earlier arm. Nothing is picked unless the pass rate drops by at least ``MIN_DROP``.

Confirm, once: rows = dev8 (new, 48) + dev7 + synonym_fresh + the 203-row robustness set;
swaps built on them by the shipped default with ``CONFIRM_DRAWS`` per term and a new seed
``CONFIRM_SEED``; traps = the 114 attribute traps (v1-v3) and the 16 dev8 topic traps.
The picked arm ships on only if, against the shipped default on the same swaps, its pass
rate drops by at least ``MIN_DROP`` absolute and ``MIN_REL_DROP`` relative, it loses at
most ``MAX_LOST_CONFIRM`` confirm ANSWER rows (dev8 wordy rows included), opens no
attribute trap and opens no more dev8 topic traps than the shipped default.
"""

from __future__ import annotations

ARMS: dict[str, dict] = {
    "shipped": {},
    "all": {"grounding_nonkey_rule": "all"},
    "corpus": {"grounding_nonkey_rule": "corpus"},
    "idf_q25": {"grounding_nonkey_rule": "idf", "grounding_nonkey_idf_quantile": 0.25},
    "idf_q50": {"grounding_nonkey_rule": "idf", "grounding_nonkey_idf_quantile": 0.50},
    "cov_065": {"grounding_threshold": 0.65},
}
CAL_FILES = tuple(f"data/eval/synonym_dev{i}.jsonl" for i in range(2, 7))
DEV8_FILE = "data/eval/nonkey_dev8.jsonl"
CONFIRM_FILES = (DEV8_FILE, "data/eval/synonym_dev7.jsonl", "data/eval/synonym_fresh.jsonl")
TRAP_FILES = tuple(f"data/eval/{n}.jsonl" for n in ("attribute_traps", "attribute_traps_v2", "attribute_traps_v3"))
CAL_DRAWS = 3
CAL_SEED = 1107
CONFIRM_DRAWS = 3
CONFIRM_SEED = 1109
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
        if name == "shipped" or name not in scores or not eligible(scores[name], ref):
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
