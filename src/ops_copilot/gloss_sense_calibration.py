"""Dev-only calibration of the gloss-sense write backoff.

Uses a hand-written verb list (``data/write/gloss_sense_dev.jsonl``) of
verbs that are in no ontology lexicon and in no held-out word list, plus
one clean-golden ``run_eval`` of the chosen setting. Held-out synonym rows
are never loaded. The pre-registered go / no-go for turning the backoff on
by default is decided on a later held-out run of the chosen setting:

- held-out ANSWER/WRITE correct must not fall;
- no new fail-open, spurious PROPOSE_WRITE, or raw PII/secret;
- clean golden stays at 1.000.

Chooses (min_score, margin, min_gloss_cosine) by maximising verb-list
accuracy, then preferring higher min_score / margin / min_cos on ties.
``gloss_sense_grounding`` stays False.
"""

from __future__ import annotations

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.eval import run_eval
from ops_copilot.gloss_sense import GlossSenseBackoff
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token
from ops_copilot.write_ontology import verb_index

DEV_SET = Path(__file__).resolve().parents[2] / "data" / "write" / "gloss_sense_dev.jsonl"


def load_dev_verbs(path: Path | None = None) -> list[dict]:
    rows = []
    for line in (path or DEV_SET).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _assert_dev_list_safe(rows: list[dict]) -> None:
    held = {fold_token(w) for w in load_split()["heldout_words"]}
    onto = set(verb_index())
    for r in rows:
        v = r["verb"]
        assert fold_token(v) not in held, f"dev verb {v} is held-out"
        assert v not in onto, f"dev verb {v} is an ontology verb"


def _verb_accuracy(gs: GlossSenseBackoff, rows: list[dict]) -> dict:
    correct = 0
    per = []
    for r in rows:
        m = gs.match_action(r["verb"], r["kind"])
        predicted = m["action"] if m and m.get("accepted") else "none"
        ok = predicted == r["label"]
        correct += int(ok)
        per.append(
            {
                "verb": r["verb"],
                "kind": r["kind"],
                "label": r["label"],
                "predicted": predicted,
                "accepted": bool(m and m.get("accepted")),
                "score": None if not m else m.get("score"),
                "ok": ok,
            }
        )
    return {"accuracy": correct / len(rows) if rows else 0.0, "n": len(rows), "per_row": per}


def calibrate() -> dict:
    rows = load_dev_verbs()
    _assert_dev_list_safe(rows)

    # Off baseline: every verb predicted "none"
    n_none = sum(1 for r in rows if r["label"] == "none")
    baseline_verbs = n_none / len(rows)
    clean_off = run_eval(Copilot(config=CopilotConfig(use_gloss_sense_backoff=False)))
    baseline = {
        "setting": "off",
        "clean_accuracy": sum(s.match for s in clean_off.scores) / len(clean_off.scores),
        "n_clean": len(clean_off.scores),
        "n_fail_open": sum(
            1
            for s in clean_off.scores
            if s.expect_decision != "ANSWER" and s.actual_decision == "ANSWER"
        ),
        "n_spurious_write": sum(
            1
            for s in clean_off.scores
            if s.expect_decision != "PROPOSE_WRITE" and s.actual_decision == "PROPOSE_WRITE"
        ),
        "verb_accuracy": baseline_verbs,
        "n_verbs": len(rows),
    }

    gs = GlossSenseBackoff(min_score=0.0, margin=0.0, min_gloss_cosine=0.0)
    for r in rows:
        gs.match_action(r["verb"], r["kind"])  # warm caches

    grid = []
    for min_score in (1.0, 1.5, 2.0, 2.5, 3.0):
        for margin in (0.0, 0.15, 0.25, 0.4):
            for min_cos in (0.25, 0.35, 0.5):
                gs.min_score = min_score
                gs.margin = margin
                gs.min_gloss_cosine = min_cos
                verb = _verb_accuracy(gs, rows)
                grid.append(
                    {
                        "min_score": min_score,
                        "margin": margin,
                        "min_gloss_cosine": min_cos,
                        "verb_accuracy": verb["accuracy"],
                        "n_verbs": verb["n"],
                    }
                )

    grid.sort(
        key=lambda r: (-r["verb_accuracy"], -r["min_score"], -r["margin"], -r["min_gloss_cosine"])
    )
    chosen_meta = grid[0]
    gs.min_score = chosen_meta["min_score"]
    gs.margin = chosen_meta["margin"]
    gs.min_gloss_cosine = chosen_meta["min_gloss_cosine"]
    verb = _verb_accuracy(gs, rows)

    cfg = CopilotConfig(
        use_gloss_sense_backoff=True,
        gloss_sense_grounding=False,
        gloss_sense_min_score=chosen_meta["min_score"],
        gloss_sense_margin=chosen_meta["margin"],
        gloss_sense_min_gloss_cosine=chosen_meta["min_gloss_cosine"],
    )
    clean_on = run_eval(Copilot(config=cfg))
    clean_acc = sum(s.match for s in clean_on.scores) / len(clean_on.scores)
    n_fail_open = sum(
        1
        for s in clean_on.scores
        if s.expect_decision != "ANSWER" and s.actual_decision == "ANSWER"
    )
    n_spurious = sum(
        1
        for s in clean_on.scores
        if s.expect_decision != "PROPOSE_WRITE" and s.actual_decision == "PROPOSE_WRITE"
    )
    chosen = {
        **chosen_meta,
        "clean_accuracy": clean_acc,
        "n_clean": len(clean_on.scores),
        "n_fail_open": n_fail_open,
        "n_spurious_write": n_spurious,
        "per_row": verb["per_row"],
        "verb_accuracy": verb["accuracy"],
    }
    return {
        "baseline_off": baseline,
        "chosen": chosen,
        "results": grid,
        "n_safe": sum(1 for r in grid if r["verb_accuracy"] == 1.0),
        "default_on_candidate": (
            chosen["verb_accuracy"] >= baseline["verb_accuracy"]
            and chosen["clean_accuracy"] == 1.0
            and chosen["n_fail_open"] == 0
            and chosen["n_spurious_write"] == 0
        ),
    }
