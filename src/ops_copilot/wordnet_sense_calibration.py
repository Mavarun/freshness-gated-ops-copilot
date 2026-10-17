"""Dev-only calibration of the WordNet noun-sense read-path backoff.

Grid (fixed before any held-out run): scope in {known, all}; max_path in
{0, 1, 2}; for path 2 the sibling fan-out cap in {10, 25, 50};
max_neighbours in {1, 2}. (Scope was added after the first clean-only run:
with scope "all" every setting broke a clean NO_EVIDENCE trap.) Scored on the
51 clean golden rows and the 15 *dev* synonym rows only; held-out rows are
never scored here.

Safe = clean 1.000, 0 fail-open, 0 spurious PROPOSE_WRITE, dev accuracy not
below the flag-off baseline. Selection: safe first, then dev accuracy, then
dev ANSWER rows, then the *most conservative* setting (known scope, shorter path, smaller
fan-out, fewer neighbours), so a tie never buys recall the dev rows did not
ask for.

Pre-registered go / no-go for default-on (a single later held-out run):
held-out accuracy and held-out ANSWER rows do not fall, nothing fails open,
no spurious write or raw PII, clean stays 1.000.
"""

from __future__ import annotations

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense_calibration import _clean_stats, _dev_synonym_accuracy

GRID_PATHS = (0, 1, 2)
GRID_FANOUT = (10, 25, 50)
GRID_NEIGHBOURS = (1, 2)
GRID_SCOPES = ("known", "all")


def grid_settings() -> list[dict]:
    out = []
    for scope in GRID_SCOPES:
        for path in GRID_PATHS:
            for fan in GRID_FANOUT if path == 2 else (0,):
                for n in GRID_NEIGHBOURS:
                    out.append(
                        {"scope": scope, "max_path": path, "max_fanout": fan, "max_neighbours": n}
                    )
    return out


def config_for(setting: dict) -> CopilotConfig:
    return CopilotConfig(
        use_wordnet_noun_sense=True,
        wordnet_max_path=setting["max_path"],
        wordnet_max_fanout=setting["max_fanout"],
        wordnet_max_neighbours=setting["max_neighbours"],
        wordnet_scope=setting["scope"],
    )


def selection_key(r: dict) -> tuple:
    return (
        -int(r["safe"]),
        -r["dev_synonym_accuracy"],
        -r["dev_answer_correct"],
        r["scope"] != "known",
        r["max_path"],
        r["max_fanout"],
        r["max_neighbours"],
    )


def calibrate(settings: list[dict] | None = None) -> dict:
    off = CopilotConfig(use_wordnet_noun_sense=False)
    baseline = {**_clean_stats(off), **_dev_synonym_accuracy(off), "setting": "off"}
    rows = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        stats = {**_clean_stats(cfg), **_dev_synonym_accuracy(cfg)}
        safe = (
            stats["clean_accuracy"] == 1.0
            and stats["n_fail_open"] == 0
            and stats["n_spurious_write"] == 0
            and stats["dev_synonym_accuracy"] >= baseline["dev_synonym_accuracy"]
        )
        rows.append({**st, **stats, "safe": safe})
    rows.sort(key=selection_key)
    return {
        "baseline_off": baseline,
        "chosen": rows[0],
        "results": rows,
        "n_safe": sum(r["safe"] for r in rows),
        "default_on_candidate": bool(rows[0]["safe"]),
    }
