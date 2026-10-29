"""Pre-registered protocol for the Oct 29 passphrase knobs (committed before any scored run).

Question: on passphrases drawn from a real diceware list (``passphrase_wordlist``),
do the off-by-default ``tail="keep"`` span and the pair-cosine incoherence arm
(``passphrase.CuedPassphraseDetector``) cut leaked passphrase words without new
false positives?

What was looked at before this file: one scratch run of the *shipped* detector on
600 rows of seed 999 (23 leaking rows: 10 tail-trim, 6 ops-only, 1 stop word
inside, 6 other) and, while designing the arm, the pair-cosine distributions of
2,000 random EFF 4-word draws and of the 55 four-plus-word runs after a credential
noun in Stack Exchange *train* sentences. Neither seed below, and no Stack Exchange
test sentence, was scored by any arm before this file was committed.

Grid: ``tail`` in {trim, keep} x ``coherence_max`` in {None, 0.02, 0.05, 0.08,
0.10, 0.12, 0.15} = 14 arms; (trim, None) is the shipped detector.

Calibration (``CALIB_SEED``, ``N_ROWS`` rows; Stack Exchange train split). An arm is
*safe* when

1. no word of the Oct 13 synthetic probe leaks (``explain_eval`` section 7 rows,
   trace query field);
2. no trace ``query`` of the 51 golden, 203 perturbed and 39 phrasal-write rows
   changes versus the shipped detector;
3. it flags at most ``FP_BUDGET_TRAIN`` more Stack Exchange train sentences than
   the shipped detector (0.5% of the 3,020 candidates);
4. it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per probe
   row than the shipped detector.

Pick: the safe arm with the fewest leaked words; ties go to fewer over-redacted
words, then ``trim`` before ``keep``, then no arm before a smaller cut.

One-shot confirm (``CONFIRM_SEED``, Stack Exchange test split). The pick ships on
(its knobs become the module defaults) only if it leaks strictly fewer words than
the shipped detector on the confirm rows, checks 1, 2 and 4 hold there, and it
flags at most ``FP_BUDGET_TEST`` more test sentences. Otherwise it ships off and
the confirm seed is spent either way.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any, Iterable

CALIB_SEED = 2910
CONFIRM_SEED = 2929
N_ROWS = 1200
TAILS = ("trim", "keep")
COHERENCE_CUTS = (None, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15)
FP_BUDGET_TRAIN = 15
FP_BUDGET_TEST = 1
OVER_BUDGET_PER_ROW = 0.5
SHIPPED = ("trim", None)

_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def arms() -> list[tuple[str, float | None]]:
    return [(t, c) for t in TAILS for c in COHERENCE_CUTS]


def arm_name(arm: tuple[str, float | None]) -> str:
    t, c = arm
    return f"{t}/{'none' if c is None else f'{c:.2f}'}"


def detector(arm: tuple[str, float | None]):
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(tail=arm[0], coherence_max=arm[1])


def patterns_for(arm: tuple[str, float | None]):
    from ops_copilot.explain_redact import SENSITIVE_PATTERNS

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in SENSITIVE_PATTERNS)


def repo_queries() -> list[str]:
    from ops_copilot.eval import load_golden
    from ops_copilot.paraphrase_set import load_paraphrase_set
    from ops_copilot.write_eval import load_phrasal_eval

    return [r["query"] for r in (*load_golden(), *load_paraphrase_set(), *load_phrasal_eval())]


def oct13_probe_texts() -> list[tuple[str, list[str]]]:
    from ops_copilot.explain_eval import PASSPHRASE_TEMPLATES, _passphrase_words, synthetic_passphrases

    return [
        (tpl.format(s=secret), _passphrase_words(secret))
        for _, secret in synthetic_passphrases()
        for tpls in PASSPHRASE_TEMPLATES.values()
        for tpl in tpls
    ]


def se_candidates(raw_dir: Path) -> dict[str, list[str]]:
    """Sentences of the QA snapshot with a credential noun and a word run, by split."""
    from ops_copilot.passphrase import CUED_RE
    from ops_copilot.qa_translation import clean_markdown, is_test

    out: dict[str, list[str]] = {"train": [], "test": []}
    for f in sorted(Path(raw_dir).glob("*.json.gz")):
        site = f.name.split("-")[0]
        for q in json.loads(gzip.decompress(f.read_bytes())).get("items", []):
            split = "test" if is_test(site, int(q["question_id"])) else "train"
            texts = [q.get("title", "")] + [clean_markdown(a.get("body_markdown", "")) for a in (q.get("answers") or [])[:2]]
            for t in texts:
                out[split].extend(s for s in _SENT.split(t) if CUED_RE.search(s))
    return out


def se_flags(det, sentences: Iterable[str]) -> dict[str, Any]:
    flagged, words, examples = 0, 0, []
    for s in sentences:
        hits = [m.group() for m in det.finditer(s)]
        if hits:
            flagged += 1
            words += sum(len(h.split()) for h in hits)
            if len(examples) < 12:
                examples.append(hits)
    return {"flagged": flagged, "redacted_words": words, "examples": examples}


def evaluate_arm(arm, rows, se_sentences: list[str], *, base_queries: dict[str, str] | None = None) -> dict[str, Any]:
    from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows

    pats = patterns_for(arm)
    probe = score_rows(rows, pats)
    oct13 = sum(sum(_present(redact_query(t, pats).lower(), w) for w in ws) for t, ws in oct13_probe_texts())
    changed = None
    if base_queries is not None:
        changed = sum(redact_query(q, pats) != red for q, red in base_queries.items())
    return {
        "arm": arm_name(arm),
        "probe": probe,
        "oct13_leak_words": oct13,
        "repo_query_changes": changed,
        "se": se_flags(detector(arm), se_sentences),
    }


def shipped_repo_queries() -> dict[str, str]:
    from ops_copilot.passphrase_wordlist import redact_query

    pats = patterns_for(SHIPPED)
    return {q: redact_query(q, pats) for q in dict.fromkeys(repo_queries())}


def is_safe(res: dict, base: dict, *, fp_budget: int) -> dict[str, bool]:
    n = res["probe"]["total"]["rows"]
    return {
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "fp_budget": res["se"]["flagged"] - base["se"]["flagged"] <= fp_budget,
        "over_budget": (res["probe"]["total"]["over_words"] - base["probe"]["total"]["over_words"]) <= OVER_BUDGET_PER_ROW * n,
    }


def pick(results: list[dict], base: dict) -> dict | None:
    safe = [r for r in results if all(is_safe(r, base, fp_budget=FP_BUDGET_TRAIN).values())]
    if not safe:
        return None
    order = {arm_name(a): i for i, a in enumerate(arms())}
    return min(
        safe,
        key=lambda r: (r["probe"]["total"]["leak_words"], r["probe"]["total"]["over_words"], order[r["arm"]]),
    )
