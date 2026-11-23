"""Pre-registered protocol for the duplicate-question paraphrase backoff (frozen 2026-11-23).

Written after the table was built and before any eval row, swap or held-out row was
scored with a ``use_dupe_paraphrase`` arm. Disclosure, in full: the table builder was
checked on synthetic titles (``tests/test_dupe_paraphrase.py``) and on 885 API-fetched
Server Fault pairs before the dump-based build replaced the API fetch; on those 885
pairs the dev split's single words were looked up once (``update`` -> ``patch`` was the
only dev gold pair present; ``usage`` gave ``free``, ``reporting``). The committed
dump-based table (78,895 pairs) was checked only for its hash, counts and symmetry; no
word of any split was looked up in it. No held-out pair, no dev10 row and no other eval
word was looked up, the shipped default alone was scored once on the calibration rows
and swaps to time the run (52 of 165 ANSWER rows, 14 of 384 swaps, 5 of 144 must-refuse
rows open), and the gates below were not tuned:
they are the textbook chi-square critical values (G² >= 15.13 is p < 1e-4, 10.83 is
p < 1e-3 at one degree of freedom) and "seen as a replacement at least twice as often
as next to it" (strict) or "at least as often" (loose).

Arms: ``strict`` (cross >= 3, G² >= 15.13, cross / (same + 1) >= 2) on scopes
``known`` / ``lone`` / ``all``, and ``loose`` (cross >= 2, G² >= 10.83, ratio >= 1) on
``lone`` / ``all``. One neighbour per word, chained after the existing noun backoffs
(all off by default, so the table is the only noun backoff in every arm).

Calibration: golden (51) + dev2-dev6 + dev8 (320 rows, as on Nov 10 / 11) and the
swap null control's 384 swaps (golden + dev2-dev6, drawn with the pre-Nov 17 default,
``CAL_DRAWS`` per term, seed ``CAL_SEED``). A synonym backoff is what can let a random
swapped-in word pass, so the swap pass rate is a safety metric.

Eligible arm (as on Nov 11): opens no more must-refuse rows than the shipped default,
raises the swap pass rate by at most ``MAX_SWAP_RISE`` absolute, adds no new
wrong-evidence answer (``citation_keep.citation_counts``) and answers at least
``MIN_GAIN_CAL`` more ANSWER rows. Pick: largest gain; ties go to the lower swap pass
rate, then the earlier arm. Nothing picked means no confirm and dev10 stays unseen.

Confirm, once: dev10 (unseen) + dev7 + synonym_fresh + the 203-row robustness set; swaps
built on them by the shipped default, ``CONFIRM_DRAWS`` per term, new seed
``CONFIRM_SEED``; traps = the 114 attribute traps (v1-v3). The picked arm ships on only
if it answers at least ``MIN_GAIN_CONFIRM`` more ANSWER rows, opens no more must-refuse
rows, opens no attribute trap, raises the swap pass rate by at most ``MAX_SWAP_RISE`` and
adds no new wrong-evidence answer. Held-out ANSWER (9 rows of the 203-row set) is
reported, not gated, as in every earlier slice.
"""

from __future__ import annotations

from ops_copilot import resource_agreement_protocol as _nov11
from ops_copilot import swap_null_protocol as _swaps

_ON = {"use_dupe_paraphrase": True}
STRICT = {"dupe_min_cross": 3, "dupe_min_g2": 15.13, "dupe_min_ratio": 2.0}
LOOSE = {"dupe_min_cross": 2, "dupe_min_g2": 10.83, "dupe_min_ratio": 1.0}
ARMS: dict[str, dict] = {
    "shipped": {},
    "strict_known": {**_ON, **STRICT, "dupe_scope": "known"},
    "strict_lone": {**_ON, **STRICT, "dupe_scope": "lone"},
    "strict_all": {**_ON, **STRICT, "dupe_scope": "all"},
    "loose_lone": {**_ON, **LOOSE, "dupe_scope": "lone"},
    "loose_all": {**_ON, **LOOSE, "dupe_scope": "all"},
}
CAL_FILES = _nov11.CAL_FILES
SWAP_BASE_FILES = _swaps.CAL_FILES
DEV10_FILE = _nov11.DEV10_FILE
CONFIRM_FILES = _nov11.CONFIRM_FILES
TRAP_FILES = _nov11.TRAP_FILES
CAL_DRAWS = _swaps.CAL_DRAWS
CAL_SEED = _swaps.CAL_SEED
CONFIRM_DRAWS = 3
CONFIRM_SEED = 1123
MIN_GAIN_CAL = 2
MIN_GAIN_CONFIRM = 2
MAX_SWAP_RISE = 0.01

gain = _nov11.gain
swap_rise = _nov11.swap_rise


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
