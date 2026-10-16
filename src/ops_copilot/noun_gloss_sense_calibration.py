"""Dev-only calibration of the noun gloss-sense read-path backoff.

Chooses (min_gloss_cosine, max_neighbours, min_score) on clean golden +
*dev* synonym rows only. Held-out synonym rows are never scored. The
pre-registered go / no-go for default-on is a later held-out run:

- held-out ANSWER/WRITE correct must not fall;
- no new fail-open, spurious PROPOSE_WRITE, or raw PII/secret;
- clean golden stays at 1.000.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.eval import run_eval
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_split import load_split


def _clean_stats(cfg: CopilotConfig) -> dict:
    rep = run_eval(Copilot(config=cfg))
    return {
        "clean_accuracy": sum(s.match for s in rep.scores) / len(rep.scores),
        "n_clean": len(rep.scores),
        "n_fail_open": sum(
            1
            for s in rep.scores
            if s.expect_decision != "ANSWER" and s.actual_decision == "ANSWER"
        ),
        "n_spurious_write": sum(
            1
            for s in rep.scores
            if s.expect_decision != "PROPOSE_WRITE" and s.actual_decision == "PROPOSE_WRITE"
        ),
    }


def _dev_synonym_accuracy(cfg: CopilotConfig) -> dict:
    split = load_split()
    rows = [r for r in load_paraphrase_set() if r["perturbation"] == "synonym"]
    bot = Copilot(config=cfg)
    correct = 0
    n = 0
    answer_ok = 0
    answer_n = 0
    for r in rows:
        if split["rows"][r["id"]]["split"] != "dev":
            continue
        n += 1
        got = bot.ask(r["query"])
        ok = got.decision.value == r["expect_decision"]
        correct += int(ok)
        if r["expect_decision"] == "ANSWER":
            answer_n += 1
            answer_ok += int(ok)
    return {
        "dev_synonym_accuracy": correct / n if n else 0.0,
        "n_dev": n,
        "dev_answer_correct": answer_ok,
        "n_dev_answer": answer_n,
    }


def calibrate() -> dict:
    off_cfg = CopilotConfig(use_noun_gloss_sense=False)
    baseline = {**_clean_stats(off_cfg), **_dev_synonym_accuracy(off_cfg), "setting": "off"}

    grid = []
    for min_cos in (0.75, 0.80, 0.85, 0.90):
        for max_n in (1, 2):
            for min_score in (0.7, 0.9, 1.1):
                cfg = CopilotConfig(
                    use_noun_gloss_sense=True,
                    noun_gloss_sense_min_gloss_cosine=min_cos,
                    noun_gloss_sense_max_neighbours=max_n,
                    noun_gloss_sense_min_score=min_score,
                    noun_gloss_sense_known_words=True,
                )
                stats = {**_clean_stats(cfg), **_dev_synonym_accuracy(cfg)}
                safe = (
                    stats["clean_accuracy"] == 1.0
                    and stats["n_fail_open"] == 0
                    and stats["n_spurious_write"] == 0
                    and stats["dev_synonym_accuracy"] >= baseline["dev_synonym_accuracy"]
                )
                grid.append(
                    {
                        "min_gloss_cosine": min_cos,
                        "max_neighbours": max_n,
                        "min_score": min_score,
                        **stats,
                        "safe": safe,
                    }
                )

    # Prefer safe settings; among them higher min_cos, then higher min_score,
    # then more neighbours (helps health->status when state also ranks).
    # Among equally safe / equal-DEV settings, prefer the lowest cosine gate
    # (max recall under the safety constraint). This keeps health~status
    # (cos ~0.89) while still rejecting scan~image (~0.69).
    grid.sort(
        key=lambda r: (
            -int(r["safe"]),
            -r["dev_synonym_accuracy"],
            -r["dev_answer_correct"],
            r["min_gloss_cosine"],
            -r["max_neighbours"],
            -r["min_score"],
        )
    )
    chosen = grid[0]
    return {
        "baseline_off": baseline,
        "chosen": chosen,
        "results": grid,
        "n_safe": sum(1 for r in grid if r["safe"]),
        "default_on_candidate": bool(chosen["safe"]),
    }
