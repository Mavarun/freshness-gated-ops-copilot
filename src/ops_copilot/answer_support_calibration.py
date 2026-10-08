"""Calibrate the answer-support model on clean golden + dev synonym rows only.

Same calibration rows and safety bar as the word-vector and lexicon
calibrations (51 clean golden queries + the 15 ``dev`` synonym rows;
``calibration_rows`` raises if a held-out row slips in). The default config
(every backoff and embeddings off) is the base.

Grid: ``answer_support_min_score`` (the lift threshold, natural log) in
``GRID`` x ``answer_support_max_terms`` in ``MAX_TERMS`` x scope
(``answer_support_known_words`` off / on) x ``answer_support_strict``
(on / off). Selection, fixed before any run:

1. feasible: clean accuracy 1.000, zero fail-open, zero spurious
   PROPOSE_WRITE and zero raw PII outputs on the calibration rows;
2. highest calibration decision accuracy;
3. ties: strict before non-strict, then unknown words only before the known-
   word scope, then fewer rescued terms, then the midpoint of the widest
   contiguous run of optimal thresholds (max-margin, as for the embeddings).

Go / no-go, also fixed before the held-out run: the chosen setting becomes the
default only if (a) it beats the model-off accuracy on the calibration rows
(``recommend_default_on``) and (b) on the held-out synonym rows it does not
lower accuracy and adds no fail-open, spurious write or raw PII (checked by
``scripts/run_robustness.py``, reported in the README). The held-out rows are
run once, after this file's choice is committed.

``dev_word_report`` is a word-level diagnostic on the split's *dev* pairs
only: for each dev replacement word, the lift with which a word of the key it
replaced answers it.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ops_copilot.config import CopilotConfig
from ops_copilot.corpus import Corpus
from ops_copilot.pipeline import Copilot
from ops_copilot.qa_translation import AnswerSupportModel, words
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split

GRID: tuple[float, ...] = tuple(round(float(x), 2) for x in np.arange(1.0, 8.001, 0.25))
MAX_TERMS: tuple[int, ...] = (1, 2)
SCOPES: tuple[bool, ...] = (False, True)  # answer_support_known_words
STRICT: tuple[bool, ...] = (True, False)  # answer_support_strict


def _feasible(r: dict) -> bool:
    return (
        r["clean_accuracy"] == 1.0
        and r["n_fail_open"] == 0
        and r["n_spurious_write"] == 0
        and r["n_raw_pii_outputs"] == 0
    )


def select(results: list[dict]) -> dict:
    feasible = [r for r in results if _feasible(r)]
    if not feasible:
        raise RuntimeError("no feasible answer-support setting")
    best = max(r["accuracy"] for r in feasible)
    tops = [r for r in feasible if r["accuracy"] == best]
    group = min(
        {(not r["strict"], bool(r["known_words"]), int(r["max_terms"])) for r in tops}
    )
    ok = {
        r["min_score"]
        for r in tops
        if (not r["strict"], bool(r["known_words"]), int(r["max_terms"])) == group
    }
    runs: list[list[float]] = []
    for i, th in enumerate(GRID):
        if th in ok:
            if runs and i > 0 and runs[-1][-1] == GRID[i - 1]:
                runs[-1].append(th)
            else:
                runs.append([th])
    widest = max(runs, key=len)
    return {
        "min_score": float(widest[(len(widest) - 1) // 2]),
        "strict": not group[0],
        "known_words": group[1],
        "max_terms": group[2],
        "accuracy": float(best),
        "optimal_run": [float(widest[0]), float(widest[-1])],
        "n_optimal": len(tops),
    }


def recommend_default_on(baseline: dict, chosen: dict) -> bool:
    return chosen["accuracy"] > baseline["accuracy"]


def dev_word_report(path=DEFAULT_SPLIT_PATH) -> list[dict]:
    """Word-level view of the dev pairs (never the held-out ones)."""
    split = load_split(path)
    dev_words = set(split["dev_words"])
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    model = AnswerSupportModel(texts, min_score=float("-inf"))
    out: list[dict] = []
    for pair in split["dev_pairs"]:
        key, repl = (s.strip() for s in pair.split("->", 1))
        key_words = words(key)
        for tok in words(repl):
            if tok not in dev_words:
                continue
            best = model.best(tok, key_words)
            out.append(
                {
                    "pair": pair,
                    "word": tok,
                    "in_model": bool(model.candidates(tok)),
                    "key_word": best.evidence_word if best else None,
                    "lift": None if best is None else round(best.score, 3),
                }
            )
    return out


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = base or CopilotConfig()
    rows = calibration_rows()
    baseline = score(Copilot(config=replace(base, use_answer_support_model=False)), rows)
    results: list[dict] = []
    for strict in STRICT:
        for known in SCOPES:
            for mt in MAX_TERMS:
                cfg = replace(
                    base,
                    use_answer_support_model=True,
                    answer_support_strict=strict,
                    answer_support_known_words=known,
                    answer_support_max_terms=mt,
                )
                bot = Copilot(config=cfg)
                assert bot.answer_support is not None
                for th in GRID:
                    bot.answer_support.min_score = th
                    results.append(
                        {"min_score": th, "strict": strict, "known_words": known, "max_terms": mt}
                        | score(bot, rows)
                    )
    chosen = select(results)
    return {
        "calibration_rows": [rid for rid, _, _ in rows],
        "n_clean": sum(1 for _, g, _ in rows if g == "clean"),
        "n_dev": sum(1 for _, g, _ in rows if g == "dev"),
        "baseline_off": baseline,
        "chosen": chosen,
        "default_on": recommend_default_on(baseline, chosen),
        "dev_words": dev_word_report(),
        "results": results,
    }
