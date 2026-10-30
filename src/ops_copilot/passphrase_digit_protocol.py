"""Pre-registered one-shot check of ``attached_digit`` (committed before any scored run).

Question: does letting a cued word end in one glued digit (Bitwarden's
``appendRandomNumberToRandomWord`` shape, "Cascade5") cut leaked passphrase
words on such rows without new false positives elsewhere?

What was looked at before this file: the Oct 30 post-hoc run on seed 3061
(``artifacts/passphrase_compound_posthoc.md``: 452 of 1,200 rows leak under the
shipped patterns) and, while writing the knob, four hand-typed strings in
``tests/test_passphrase_attached_digit.py``. No seed below, no Stack Exchange
sentence and no Stack Exchange identifier was scored with the knob on.

There is one arm and nothing to tune, so there is no calibration split: every
check below is run once and the knob ships on only if all hold.

1. On ``ATTACHED_SEED`` rows (``number_style="attached"``) it leaks strictly
   fewer words than the shipped patterns.
2. On ``STANDARD_SEED`` rows (the Oct 29 shape) it leaks no more words, and
   over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row.
3. No Oct 13 probe word leaks; no golden / perturbed / write trace query
   changes; no ``data/`` identifier is newly flagged.
4. Stack Exchange sentences after a credential noun (either regex): at most
   ``FP_BUDGET_TRAIN`` more train and ``FP_BUDGET_TEST`` more test sentences flagged.
5. Stack Exchange identifiers, the alphabetic set of ``passphrase_identifiers``
   plus the names with a glued digit part (``python3-pip-wheel``): new flags at
   most ``max(ident floor, 0.5%)`` of each split (floors 9 train, 1 test).
"""

from __future__ import annotations

import gzip
import json
import math
import re
from pathlib import Path
from typing import Any

ATTACHED_SEED = 3079
STANDARD_SEED = 3083
N_ROWS = 1200
FP_BUDGET_TRAIN = 15
FP_BUDGET_TEST = 1
IDENT_FLOOR = {"train": 9, "test": 1}
OVER_BUDGET_PER_ROW = 0.5

IDENT_DIGIT_RE = re.compile(r"(?<![\w./-])[A-Za-z]{3,12}\d?(?:([-._])[A-Za-z]{3,12}\d?)(?:\1[A-Za-z]{3,12}\d?){1,4}(?![\w-])")


def ident_budget(split: str, n: int) -> int:
    return max(IDENT_FLOOR[split], math.floor(0.005 * n))


def shipped_detector():
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True, attached_digit=False,
    )


def candidate_detector():
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True, attached_digit=True,
    )


def patterns_with(det):
    from ops_copilot import passphrase_compound_protocol as C

    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def se_material(raw_dir: Path) -> dict[str, dict[str, list[str]]]:
    """Per split: candidate sentences (either cue regex) and identifiers (alphabetic + glued digit)."""
    from ops_copilot.passphrase import CUED_DIGIT_RE, CUED_RE
    from ops_copilot.passphrase_identifiers import IDENT_RE
    from ops_copilot.passphrase_tail_protocol import _SENT
    from ops_copilot.qa_translation import clean_markdown, is_test

    sent: dict[str, list[str]] = {"train": [], "test": []}
    ids: dict[str, set[str]] = {"train": set(), "test": set()}
    for f in sorted(Path(raw_dir).glob("*.json.gz")):
        site = f.name.split("-")[0]
        for q in json.loads(gzip.decompress(f.read_bytes())).get("items", []):
            split = "test" if is_test(site, int(q["question_id"])) else "train"
            texts = [q.get("title", "")] + [clean_markdown(a.get("body_markdown", "")) for a in (q.get("answers") or [])[:2]]
            for t in texts:
                sent[split].extend(s for s in _SENT.split(t) if CUED_RE.search(s) or CUED_DIGIT_RE.search(s))
                ids[split].update(m.group() for m in IDENT_RE.finditer(t))
                ids[split].update(m.group() for m in IDENT_DIGIT_RE.finditer(t))
    ids["test"] -= ids["train"]
    return {sp: {"sentences": sent[sp], "identifiers": sorted(ids[sp])} for sp in ("train", "test")}


def checks(res: dict[str, Any]) -> dict[str, bool]:
    a, s = res["attached"], res["standard"]
    n = s["shipped"]["rows"]
    out = {
        "attached_fewer_leaks": a["candidate"]["leak_words"] < a["shipped"]["leak_words"],
        "standard_no_more_leaks": s["candidate"]["leak_words"] <= s["shipped"]["leak_words"],
        "standard_over_budget": s["candidate"]["over_words"] - s["shipped"]["over_words"] <= OVER_BUDGET_PER_ROW * n,
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "data_idents": not res["data_ident_new_flags"],
    }
    if "se" in res:
        for sp, budget in (("train", FP_BUDGET_TRAIN), ("test", FP_BUDGET_TEST)):
            e = res["se"][sp]
            out[f"se_{sp}_sentences"] = e["sent_candidate"] - e["sent_shipped"] <= budget
            out[f"se_{sp}_identifiers"] = e["ident_new"] <= ident_budget(sp, e["n_identifiers"])
    return out
