"""Citation-aware re-run of the non-key compound-parts protocol (frozen 2026-11-17).

Written before anything below was run: no arm has been scored with citation counts on
the calibration rows, and no config has been run on any dev9 row or on the seed-1110
confirm swaps. Disclosure, in full, of what was already known when this was frozen:

- the Nov 10 calibration (``artifacts/nonkey_parts_calibration.md``): all three parts arms
  tie at 14 of 384 swaps and lose the same 3 rows (``d5-22``, ``d6-06``, ``d8-30``);
- the Nov 10 post-hoc reading: ``d6-06`` is answered by the shipped default from the
  latency runbook (wrong evidence), ``d5-22`` is a golden-derived genuine loss and
  ``d8-30`` has no clean source question (no evidence label);
- the citation-aware keep count (``citation_keep``), pre-registered on Nov 11 for dev9
  after that calibration was seen.

So the calibration re-score below is *not* independent evidence: with the Nov 11 rule,
the expected outcome is that ``d6-06`` counts as fixed, the budget count is 2 and the
earliest tied arm, ``all_hyphen``, is picked. It only decides which frozen arm goes to
the confirm, by a rule written down before the re-score. dev9 is the clean test.

Calibration (re-score): the Nov 10 rows (golden + dev2-dev6 + dev8, 320) and the same
384 swaps (``CAL_DRAWS`` per term, seed ``CAL_SEED``). Eligible arm: citation budget
count (``lost + unknown_lost``) at most ``MAX_LOST_CAL``, no new wrong-evidence answer,
no more must-refuse rows opened than the shipped default. Pick: lowest swap pass rate,
ties to the lower budget count, then the earlier arm; nothing is picked unless the pass
rate drops by at least ``MIN_DROP``. The Nov 9 ``all`` arm stays reference-only.

Confirm, once (the Nov 10 confirm that was never run, unchanged except for the count):
rows = dev9 wordy (32, unseen) + dev7 + synonym_fresh + the 203-row robustness set;
swaps built on them by the shipped default with ``CONFIRM_DRAWS`` per term and seed
``CONFIRM_SEED`` = 1110; traps = the 114 attribute traps and the 16 dev9 topic traps.
Evidence labels: ``data/eval/nonkey_dev9_docs.json`` for dev9 rows, the clean source
question's citations for golden-derived rows, unknown otherwise. The picked arm ships on
only if, against the shipped default on the same swaps, the pass rate drops by at least
``MIN_DROP`` absolute and ``MIN_REL_DROP`` relative, the citation budget count is at most
``MAX_LOST_CONFIRM``, it adds no new wrong-evidence answer, opens no attribute trap and
opens no more dev9 topic traps than the shipped default. The decision-only lost count and
held-out ANSWER (9 rows of the 203-row set) are reported, not gated.
"""

from __future__ import annotations

from ops_copilot import nonkey_parts_protocol as _nov10

ARMS: dict[str, dict] = dict(_nov10.ARMS)
REFERENCE_ONLY = _nov10.REFERENCE_ONLY
EXPECTED_PICK = "all_hyphen"
CAL_FILES = _nov10.CAL_FILES
SWAP_BASE_FILES = _nov10.SWAP_BASE_FILES
DEV9_FILE = _nov10.DEV9_FILE
CONFIRM_FILES = _nov10.CONFIRM_FILES
TRAP_FILES = _nov10.TRAP_FILES
CAL_DRAWS = _nov10.CAL_DRAWS
CAL_SEED = _nov10.CAL_SEED
CONFIRM_DRAWS = _nov10.CONFIRM_DRAWS
CONFIRM_SEED = _nov10.CONFIRM_SEED
MAX_LOST_CAL = 2
MAX_LOST_CONFIRM = 2
MIN_DROP = 0.03
MIN_REL_DROP = 0.25


def eligible(arm: dict, ref: dict, cites: dict) -> bool:
    return (
        cites["budget_lost"] <= MAX_LOST_CAL
        and not cites["new_wrong"]
        and arm["refuse_opened"] <= ref["refuse_opened"]
    )


def pick(scores: dict[str, dict], cites: dict[str, dict]) -> str | None:
    """Arm picked from ``{arm: NullScore.as_dict()}`` and ``{arm: citation_counts(...)}``."""
    ref = scores["shipped"]
    ref_rate = ref["rates"]["null_pass_rate"]
    best, best_key = None, None
    for i, name in enumerate(ARMS):
        if name == "shipped" or name in REFERENCE_ONLY or name not in scores or name not in cites:
            continue
        if not eligible(scores[name], ref, cites[name]):
            continue
        rate = scores[name]["rates"]["null_pass_rate"]
        if ref_rate - rate < MIN_DROP:
            continue
        key = (rate, cites[name]["budget_lost"], i)
        if best_key is None or key < best_key:
            best, best_key = name, key
    return best


def ships(arm: dict, ref: dict, cites: dict, attr_opens: int, topic_opens: int, ref_topic_opens: int) -> bool:
    a, r = arm["rates"]["null_pass_rate"], ref["rates"]["null_pass_rate"]
    drop = r - a
    return (
        drop >= MIN_DROP
        and (r > 0 and drop / r >= MIN_REL_DROP)
        and cites["budget_lost"] <= MAX_LOST_CONFIRM
        and not cites["new_wrong"]
        and attr_opens == 0
        and topic_opens <= ref_topic_opens
    )
