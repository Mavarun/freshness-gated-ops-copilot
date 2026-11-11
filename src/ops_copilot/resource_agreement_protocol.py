"""Pre-registered protocol for the resource-agreement backoff (frozen 2026-11-11).

Written before the calibration grid was run and before any dev10 row, confirm swap or
held-out row was scored with an agreement arm. Disclosure, in full: before the knob was
written, the five resources were probed on the dev split's 57 single-word pairs (never
on held-out pairs): with loose per-resource gates, the gold corpus word was among the
candidates two or more resources agree on for 9 of 57 dev pairs, next to many wrong
ones (``open`` for ``clear``, ``firing`` for ``release``, ``password`` for ``secret``).
A domain-vector filter and Hearst-style patterns mined from the Stack Exchange snapshot
were also probed on dev pairs and dropped (2-3 of 42 unknown dev words recovered; 549
noisy pattern pairs). The unit tests ran spot lookups of ``usage``. Nothing else.

Arms: ``min_votes`` 2 or 3 crossed with scope ``known`` / ``all``, plus 2-vote ``lone``.

Calibration: golden (51) + dev2-dev6 + dev8 (320 rows, as on Nov 10) and the same 384
swaps as the Nov 7 / 9 / 10 protocols (built on golden + dev2-dev6, ``CAL_DRAWS`` per
term, seed ``CAL_SEED``). A synonym backoff is exactly what can let a random swapped-in
word pass, so the swap pass rate is a safety metric here.

Eligible arm: opens no more must-refuse rows than the shipped default, raises the swap
pass rate by at most ``MAX_SWAP_RISE`` absolute, adds no new wrong-evidence answer
(``citation_keep.citation_counts``) and answers at least ``MIN_GAIN_CAL`` more ANSWER rows
than the shipped default. Pick: largest gain; ties go to the lower swap pass rate, then
the earlier arm. Nothing picked means no confirm.

Confirm, once: rows = dev10 (26, unseen) + dev7 + synonym_fresh + the 203-row robustness
set (its 35 held-out synonym rows are the held-out run); swaps built on them by the
shipped default with ``CONFIRM_DRAWS`` per term and a new seed ``CONFIRM_SEED``; traps =
the 114 attribute traps (v1-v3). The picked arm ships on only if, against the shipped
default, it answers at least ``MIN_GAIN_CONFIRM`` more ANSWER rows, opens no more
must-refuse rows, opens no attribute trap, raises the swap pass rate by at most
``MAX_SWAP_RISE`` and adds no new wrong-evidence answer. Held-out ANSWER (the 9 held-out
ANSWER rows of the 203-row set) is reported, not gated, as in every earlier slice.
"""

from __future__ import annotations

from ops_copilot import nonkey_parts_protocol as _nov10

_ON = {"use_resource_agreement": True}
ARMS: dict[str, dict] = {
    "shipped": {},
    "agree2_known": {**_ON, "agreement_min_votes": 2, "agreement_scope": "known"},
    "agree3_known": {**_ON, "agreement_min_votes": 3, "agreement_scope": "known"},
    "agree2_lone": {**_ON, "agreement_min_votes": 2, "agreement_scope": "lone"},
    "agree2_all": {**_ON, "agreement_min_votes": 2, "agreement_scope": "all"},
    "agree3_all": {**_ON, "agreement_min_votes": 3, "agreement_scope": "all"},
}
CAL_FILES = _nov10.CAL_FILES
SWAP_BASE_FILES = _nov10.SWAP_BASE_FILES
DEV10_FILE = "data/eval/synonym_dev10.jsonl"
CONFIRM_FILES = (DEV10_FILE, "data/eval/synonym_dev7.jsonl", "data/eval/synonym_fresh.jsonl")
TRAP_FILES = _nov10.TRAP_FILES
CAL_DRAWS = _nov10.CAL_DRAWS
CAL_SEED = _nov10.CAL_SEED
CONFIRM_DRAWS = 3
CONFIRM_SEED = 1111
MIN_GAIN_CAL = 2
MIN_GAIN_CONFIRM = 2
MAX_SWAP_RISE = 0.01


def gain(arm: dict, ref: dict) -> int:
    return arm["answered"] - ref["answered"]


def swap_rise(arm: dict, ref: dict) -> float:
    return arm["rates"]["null_pass_rate"] - ref["rates"]["null_pass_rate"]


def eligible(arm: dict, ref: dict, new_wrong: int) -> bool:
    return (
        arm["refuse_opened"] <= ref["refuse_opened"]
        and swap_rise(arm, ref) <= MAX_SWAP_RISE + 1e-12
        and new_wrong == 0
        and gain(arm, ref) >= MIN_GAIN_CAL
    )


def pick(scores: dict[str, dict], new_wrong: dict[str, int]) -> str | None:
    """Arm picked from ``{arm: NullScore.as_dict()}`` and per-arm new wrong-evidence counts."""
    ref = scores["shipped"]
    best, best_key = None, None
    for i, name in enumerate(ARMS):
        if name == "shipped" or name not in scores:
            continue
        if not eligible(scores[name], ref, new_wrong.get(name, 0)):
            continue
        key = (-gain(scores[name], ref), scores[name]["rates"]["null_pass_rate"], i)
        if best_key is None or key < best_key:
            best, best_key = name, key
    return best


def ships(arm: dict, ref: dict, attr_opens: int, new_wrong: int) -> bool:
    return (
        gain(arm, ref) >= MIN_GAIN_CONFIRM
        and arm["refuse_opened"] <= ref["refuse_opened"]
        and attr_opens == 0
        and swap_rise(arm, ref) <= MAX_SWAP_RISE + 1e-12
        and new_wrong == 0
    )
