"""Calibrate the passage-level answer-support backoff on clean golden + dev rows only.

Same calibration rows and safety bar as every earlier backoff (51 clean
golden queries + the 15 ``dev`` synonym rows; ``calibration_rows`` raises if
a held-out row slips in). The default config (every backoff and embeddings
off) is the base.

Grid: ``passage_support_min_prob`` in ``GRID`` x ``passage_support_max_terms``
in ``MAX_TERMS`` x scope (``passage_support_known_words`` off / on) x
``passage_support_strict`` (on / off). Selection, fixed before any run (the
same rule as ``answer_support_calibration``):

1. feasible: clean accuracy 1.000, zero fail-open, zero spurious
   PROPOSE_WRITE and zero raw PII outputs on the calibration rows;
2. highest calibration decision accuracy;
3. ties: strict before non-strict, then unknown words only before the known-
   word scope, then fewer rescued terms, then the midpoint of the widest
   contiguous run of optimal thresholds (max-margin).

Go / no-go, also fixed before the held-out run: the chosen setting becomes the
default only if (a) it beats the model-off accuracy on the calibration rows
(``recommend_default_on``) and (b) on the held-out synonym rows it does not
lower accuracy and adds no fail-open, spurious write or raw PII (checked by
``scripts/run_robustness.py``). The held-out rows are run once, after this
file's choice is committed.

``dev_word_report`` is a word-level diagnostic on the split's *dev* pairs
only: the domain-vector cosine between each dev replacement word and the key
word it replaced.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ops_copilot.config import CopilotConfig
from ops_copilot.domain_vectors import default_vectors
from ops_copilot.pipeline import Copilot
from ops_copilot.qa_translation import words
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split

GRID: tuple[float, ...] = tuple(round(float(x), 3) for x in np.arange(0.05, 0.951, 0.025))
MAX_TERMS: tuple[int, ...] = (1, 2)
SCOPES: tuple[bool, ...] = (False, True)  # passage_support_known_words
STRICT: tuple[bool, ...] = (True, False)  # passage_support_strict


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
        raise RuntimeError("no feasible passage-support setting")
    best = max(r["accuracy"] for r in feasible)
    tops = [r for r in feasible if r["accuracy"] == best]
    group = min({(not r["strict"], bool(r["known_words"]), int(r["max_terms"])) for r in tops})
    ok = {
        r["min_prob"]
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
        "min_prob": float(widest[(len(widest) - 1) // 2]),
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
    """Domain-vector cosine of each dev replacement word to the key it replaced."""
    split = load_split(path)
    dev_words = set(split["dev_words"])
    dv = default_vectors()
    out: list[dict] = []
    for pair in split["dev_pairs"]:
        key, repl = (s.strip() for s in pair.split("->", 1))
        key_words = words(key)
        for tok in words(repl):
            if tok not in dev_words:
                continue
            kw, sim = dv.best(tok, key_words)
            out.append(
                {
                    "pair": pair,
                    "word": tok,
                    "in_vectors": tok in dv,
                    "key_word": kw,
                    "cosine": None if kw is None else round(sim, 3),
                }
            )
    return out


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = base or CopilotConfig()
    rows = calibration_rows()
    baseline = score(Copilot(config=replace(base, use_passage_support_model=False)), rows)
    results: list[dict] = []
    for strict in STRICT:
        for known in SCOPES:
            for mt in MAX_TERMS:
                cfg = replace(
                    base,
                    use_passage_support_model=True,
                    passage_support_strict=strict,
                    passage_support_known_words=known,
                    passage_support_max_terms=mt,
                )
                bot = Copilot(config=cfg)
                assert bot.passage_support is not None
                for th in GRID:
                    bot.grounder.passage_min_prob = th
                    results.append(
                        {"min_prob": th, "strict": strict, "known_words": known, "max_terms": mt}
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
