"""WordNet noun-sense gate, re-calibrated on dev2 (pre-registered 2026-10-19).

PR #23 left the WordNet backoff off because the 15-row dev split could not
pick among fourteen safe gates and held-out had been seen twice. This module
fixes the whole protocol *before* any config is run on ``synonym_dev2``:

Calibration rows: clean golden (51) + dev synonym rows (15) + dev2 ``calib``
half (22). Held-out rows and the dev2 ``confirm`` half are never scored here.

Grid (``grid_settings``, 144 settings): scope {known, lone, all} x max_path
{0, 1, 2} (fan-out {10, 25} at path 2) x max_neighbours {1, 2} x morphy
{off, on} x max_sense_rank {1, 2, all}.

Safe (``is_safe``): clean 1.000; zero fail-open and zero spurious
PROPOSE_WRITE on every calibration row; and **no new error**: no calibration
row that the flag-off config gets right is wrong under the setting.

Selection (``selection_key``): safe first; then calibration rows correct
(dev + dev2 calib); then calibration ANSWER rows correct; then the most
conservative setting (known < lone < all scope, shorter path, smaller
fan-out, fewer neighbours, morphy off, fewer senses).

Candidate: the chosen setting must be safe **and** strictly beat flag-off on
calibration rows; otherwise the flag ships off without a confirm run.

Confirm (one shot, ``confirm_decision``): default-on only if, on the 21 dev2
``confirm`` rows, accuracy is strictly above flag-off, ANSWER rows correct do
not fall, no new error, zero fail-open / spurious write / raw PII; and on the
203-row robustness run clean stays 1.000, zero fail-open / spurious write /
raw PII, and held-out accuracy and held-out ANSWER rows do not fall.
Held-out enters as a no-harm check only (it is the third look for this
family), never as a gain criterion.
"""

from __future__ import annotations

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.pii import detect_pii
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_dev2 import half
from ops_copilot.synonym_split import load_split

GRID_SCOPES = ("known", "lone", "all")
GRID_PATHS = (0, 1, 2)
GRID_FANOUT = (10, 25)
GRID_NEIGHBOURS = (1, 2)
GRID_MORPHY = (False, True)
GRID_SENSE_RANK = (1, 2, 0)  # 0 = all senses (least conservative, ordered last)
SCOPE_RANK = {"known": 0, "lone": 1, "all": 2}
SENSE_RANK_ORDER = {1: 0, 2: 1, 0: 2}


def grid_settings() -> list[dict]:
    out = []
    for scope in GRID_SCOPES:
        for path in GRID_PATHS:
            for fan in GRID_FANOUT if path == 2 else (0,):
                for n in GRID_NEIGHBOURS:
                    for morphy in GRID_MORPHY:
                        for rank in GRID_SENSE_RANK:
                            out.append(
                                {
                                    "scope": scope,
                                    "max_path": path,
                                    "max_fanout": fan,
                                    "max_neighbours": n,
                                    "morphy": morphy,
                                    "max_sense_rank": rank,
                                }
                            )
    return out


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    from dataclasses import replace

    return replace(
        base or CopilotConfig(),
        use_wordnet_noun_sense=True,
        wordnet_scope=setting["scope"],
        wordnet_max_path=setting["max_path"],
        wordnet_max_fanout=setting["max_fanout"],
        wordnet_max_neighbours=setting["max_neighbours"],
        wordnet_morphy=setting["morphy"],
        wordnet_max_sense_rank=setting["max_sense_rank"],
    )


def calibration_rows() -> list[dict]:
    """Dev synonym rows of the 203-row set + dev2 calib half (no held-out, no confirm)."""
    split = load_split()
    dev = [
        {"id": r["id"], "query": r["query"], "expect_decision": r["expect_decision"], "set": "dev"}
        for r in load_paraphrase_set()
        if r["perturbation"] == "synonym" and split["rows"][r["id"]]["split"] == "dev"
    ]
    d2 = [{**r, "set": "dev2_calib"} for r in half("calib")]
    return dev + d2


def score_rows(cfg: CopilotConfig, rows: list[dict]) -> dict:
    bot = Copilot(config=cfg)
    per_row: dict[str, str] = {}
    fail_open = spurious = raw_pii = 0
    for r in rows:
        res = bot.ask(r["query"])
        got, want = res.decision.value, r["expect_decision"]
        per_row[r["id"]] = got
        raw_pii += bool(detect_pii(res.answer or ""))
        if got != want:
            fail_open += got == "ANSWER"
            spurious += got == "PROPOSE_WRITE"
    ok = {r["id"]: per_row[r["id"]] == r["expect_decision"] for r in rows}
    ans = [r for r in rows if r["expect_decision"] == "ANSWER"]
    return {
        "n": len(rows),
        "correct": sum(ok.values()),
        "accuracy": sum(ok.values()) / len(rows) if rows else 0.0,
        "answer_correct": sum(ok[r["id"]] for r in ans),
        "n_answer": len(ans),
        "n_fail_open": fail_open,
        "n_spurious_write": spurious,
        "n_raw_pii": raw_pii,
        "decisions": per_row,
        "ok": ok,
    }


def new_errors(off: dict, on: dict) -> list[str]:
    return sorted(k for k, v in off["ok"].items() if v and not on["ok"][k])


def fixed_rows(off: dict, on: dict) -> list[str]:
    return sorted(k for k, v in off["ok"].items() if not v and on["ok"][k])


def is_safe(clean: dict, off: dict, on: dict) -> bool:
    return (
        clean["clean_accuracy"] == 1.0
        and clean["n_fail_open"] == 0
        and clean["n_spurious_write"] == 0
        and on["n_fail_open"] == 0
        and on["n_spurious_write"] == 0
        and on["n_raw_pii"] == 0
        and not new_errors(off, on)
    )


def selection_key(r: dict) -> tuple:
    return (
        -int(r["safe"]),
        -r["calib_correct"],
        -r["calib_answer_correct"],
        SCOPE_RANK[r["scope"]],
        r["max_path"],
        r["max_fanout"],
        r["max_neighbours"],
        int(r["morphy"]),
        SENSE_RANK_ORDER[r["max_sense_rank"]],
    )


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok",)}


def calibrate(settings: list[dict] | None = None, rows: list[dict] | None = None) -> dict:
    rows = calibration_rows() if rows is None else rows
    off_cfg = CopilotConfig(use_wordnet_noun_sense=False)
    off = score_rows(off_cfg, rows)
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        results.append(
            {
                **st,
                "clean_accuracy": clean["clean_accuracy"],
                "calib_correct": on["correct"],
                "calib_accuracy": on["accuracy"],
                "calib_answer_correct": on["answer_correct"],
                "n_fail_open": on["n_fail_open"] + clean["n_fail_open"],
                "n_spurious_write": on["n_spurious_write"] + clean["n_spurious_write"],
                "n_raw_pii": on["n_raw_pii"],
                "fixed": fixed_rows(off, on),
                "new_errors": new_errors(off, on),
                "safe": is_safe(clean, off, on),
            }
        )
    results.sort(key=selection_key)
    chosen = results[0]
    return {
        "n_rows": len(rows),
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg)},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"] and chosen["calib_correct"] > off["correct"]),
        "results": results,
    }


def confirm_decision(off_confirm: dict, on_confirm: dict, off_rob: dict, on_rob: dict) -> dict:
    ho = off_rob["per_synonym_split"]["heldout"]
    hn = on_rob["per_synonym_split"]["heldout"]
    checks = {
        "confirm_gain": on_confirm["correct"] > off_confirm["correct"],
        "confirm_answer_not_down": on_confirm["answer_correct"] >= off_confirm["answer_correct"],
        "confirm_no_new_error": not new_errors(off_confirm, on_confirm),
        "confirm_no_fail_open_write_pii": on_confirm["n_fail_open"] == 0
        and on_confirm["n_spurious_write"] == 0
        and on_confirm["n_raw_pii"] == 0,
        "clean_1": on_rob["clean_accuracy"] == 1.0,
        "robustness_no_fail_open_write_pii": on_rob["n_fail_open"] == 0
        and on_rob["n_spurious_write"] == 0
        and on_rob["n_raw_pii_outputs"] == 0,
        "heldout_acc_not_down": hn["perturbed_accuracy"] >= ho["perturbed_accuracy"],
        "heldout_answer_not_down": hn["by_gate"]["ANSWER"]["correct"] >= ho["by_gate"]["ANSWER"]["correct"],
    }
    return {"checks": checks, "default_on": all(checks.values())}
