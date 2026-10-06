"""Run the refusal-explanation eval and write its artifacts.

    python scripts/run_explanation_eval.py

Writes ``artifacts/explanation_eval.{json,md}`` for the default config and
the embedding-on config (frozen MiniLM fixture), both deterministic. Exits
non-zero if any explanation leaks a canary token, PII or a secret, if a
redacted trace line (query, reason, write parse, explanation) still holds one,
or if a golden explanation check fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.explain_eval import run_explanation_eval  # noqa: E402

ART = ROOT / "artifacts"
CONFIGS = {
    "default": CopilotConfig(),
    "embedding on (frozen MiniLM)": CopilotConfig(embedding_backend="frozen"),
}


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({a / b:.3f})" if b else "0/0"


def render_md(runs: dict[str, dict]) -> str:
    lines = [
        "# Refusal-explanation eval",
        "",
        "Expectations: `data/eval/explanation_expectations.jsonl`, one hand-written row per refusing "
        "golden case (33), taken from each golden row's note. Stale ages and SLAs are recomputed "
        "from `data/corpus/*.jsonl` and `config/source_slas.yaml` independently of the pipeline. "
        "Transfer = perturbed rows refused with the same decision as their golden source, checked "
        "against that source's expectation. Leaks = canary tokens, PII, secret patterns or the "
        "literal planted values found in any explanation or refusal reason (golden, 203 perturbed, "
        "write refusals, and probe queries that paste each planted value and synthetic secrets).",
        "",
        "| config | golden rows fully correct | golden checks | schema ok (golden / perturbed) | transfer rows | transfer checks | write reason codes | did-you-mean | leaks |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, r in runs.items():
        g, p, w, lk = r["golden"], r["perturbed"], r["write_refusals"], r["leaks"]
        t = p["transfer"]
        lines.append(
            f"| {label} | {_pct(g['rows_all_correct'], g['n_rows'])} | {_pct(g['n_checks_correct'], g['n_checks'])} | "
            f"{g['n_schema_ok']}/{g['n']} / {p['n_schema_ok']}/{p['n']} | {_pct(t['rows_all_correct'], t['n_rows'])} | "
            f"{_pct(t['n_checks_correct'], t['n_checks'])} | {w['reason_code_correct']}/{w['reason_code_expected']} | "
            f"{w['suggestion_correct']}/{w['suggestion_expected']} | {lk['n_leaks']} |"
        )
    for label, r in runs.items():
        lines += ["", f"## {label}: checks", "", "| check | golden | perturbed transfer |", "|---|---|---|"]
        gb, tb = r["golden"]["by_check"], r["perturbed"]["transfer"]["by_check"]
        for name in sorted(set(gb) | set(tb)):
            gc = gb.get(name)
            tc = tb.get(name)
            lines.append(
                f"| {name} | {_pct(gc['correct'], gc['n']) if gc else '-'} | {_pct(tc['correct'], tc['n']) if tc else '-'} |"
            )
        lk = r["leaks"]
        lines += [
            "",
            f"Leak scan: {lk['n_secrets_planted']} planted values (canary tokens + corpus PII/secrets), "
            f"{lk['n_probe_queries']} probe queries ({lk['n_probe_refusals']} refused); leaks by section "
            f"{lk['by_section']}.",
        ]
        tl = r.get("trace_leaks")
        if tl:
            lines += [
                "",
                "Trace-bound fields (`query`, `reason`, `write_intent`, `proposed_write`, "
                f"`explanation`): **{tl['n_rows_raw_leaking']} rows / {tl['n_raw_leaks']} leaks "
                f"unredacted (as PR #14 wrote them) -> {tl['n_rows_redacted_leaking']} rows / "
                f"{tl['n_redacted_leaks']} leaks redacted (as written now)**.",
                "",
                "| section | rows | rows leaking raw | rows leaking redacted | raw leaks | redacted leaks |",
                "|---|---:|---:|---:|---:|---:|",
            ]
            for sec, t in tl["by_section"].items():
                lines.append(
                    f"| {sec} | {t['rows']} | {t['rows_raw_leaking']} | {t['rows_redacted_leaking']} | "
                    f"{t['raw_leaks']} | {t['redacted_leaks']} |"
                )
        failed = [x for x in r["golden"]["rows"] if x["failed"]]
        if failed:
            lines += ["", "Golden failures: " + ", ".join(f"g{x['golden_index']:02d} {x['failed']}" for x in failed)]
    return "\n".join(lines) + "\n"


def main() -> int:
    runs = {label: run_explanation_eval(cfg) for label, cfg in CONFIGS.items()}
    ART.mkdir(exist_ok=True)
    (ART / "explanation_eval.json").write_text(json.dumps(runs, indent=2, sort_keys=True) + "\n")
    (ART / "explanation_eval.md").write_text(render_md(runs))
    bad = 0
    for label, r in runs.items():
        g = r["golden"]
        print(
            f"{label:30s} golden {g['rows_all_correct']}/{g['n_rows']} rows, "
            f"{g['n_checks_correct']}/{g['n_checks']} checks; leaks={r['leaks']['n_leaks']}; "
            f"trace leaks raw={r['trace_leaks']['n_raw_leaks']} "
            f"redacted={r['trace_leaks']['n_redacted_leaks']}"
        )
        bad += r["leaks"]["n_leaks"] + (g["n_checks"] - g["n_checks_correct"])
        bad += r["trace_leaks"]["n_redacted_leaks"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
