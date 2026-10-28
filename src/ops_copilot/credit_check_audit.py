"""Post-hoc (2026-10-28, after the confirm): every veto the shipped credited-word check makes.

The calibration and confirm say *whether* the stop-word check is safe and what
it costs; this lists *what* it vetoes. For every row of every set (calibration,
dev7 confirm, all three trap sets, the fresh general-English set), the shipped
default and the pre-change default (check off) are run; each row on which the
check vetoes a rescue is recorded with the query word, the credited stop word and
the effect: ``closed`` (a must-refuse row the pre-change default opened),
``lost`` (a row that was correct and no longer is), ``relabelled`` (a refusal
that stays a refusal for another reason) or ``none``. Selects nothing and
changes no config.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from ops_copilot.attribute_traps import load_traps
from ops_copilot.attribute_traps_v2 import load_traps_v2
from ops_copilot.attribute_traps_v3 import load_traps_v3
from ops_copilot.config import CopilotConfig
from ops_copilot.credit_check import calibration_rows
from ops_copilot.fresh_synonym_eval import load_fresh
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.synonym_dev7 import half as dev7_half


def all_rows() -> list[dict]:
    out = [{**r, "set": r.get("set", "calib")} for r in calibration_rows()]
    out += [{**r, "set": "dev7_confirm"} for r in dev7_half("confirm")]
    out += [{**r, "set": s} for s, rows in (("traps_v1", load_traps()), ("traps_v2", load_traps_v2()),
                                             ("traps_v3", load_traps_v3())) for r in rows]
    out += [{"id": r["id"], "query": r["query"], "expect_decision": r["expect_decision"], "set": "fresh"}
            for r in load_fresh()]
    return out


def effect(want: str, pre: str, now: str) -> str:
    if pre == now:
        return "none"
    if want not in OPENING and pre in OPENING and now not in OPENING:
        return "closed"
    if pre == want and now != want:
        return "lost"
    if now == want and pre != want:
        return "fixed"
    return "relabelled"


def run(rows: list[dict] | None = None) -> dict:
    rows = all_rows() if rows is None else rows
    now_bot = Copilot(config=CopilotConfig())
    pre_bot = Copilot(config=replace(CopilotConfig(), passage_support_credit_stop=False))
    g = now_bot.grounder
    vetoes = []
    for r in rows:
        g.credit_log.clear()
        now = now_bot.ask(r["query"]).decision.value
        log = list(g.credit_log)
        if not log:
            continue
        pre = pre_bot.ask(r["query"]).decision.value
        vetoes.append({"id": r["id"], "set": r["set"], "query": r["query"], "expect": r["expect_decision"],
                       "pre": pre, "now": now, "effect": effect(r["expect_decision"], pre, now),
                       "credits": sorted({f"{w} <- {c}" for _, w, c, _ in log})})
    return {
        "n_rows": len(rows),
        "n_vetoed_rows": len(vetoes),
        "by_effect": dict(sorted(Counter(v["effect"] for v in vetoes).items())),
        "credited_words": dict(Counter(c.split(" <- ")[1] for v in vetoes for c in v["credits"]).most_common()),
        "vetoes": vetoes,
    }
