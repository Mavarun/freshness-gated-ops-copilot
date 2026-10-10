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
        dc = r.get("disclosure")
        if dc:
            ov = dc["over_redacted_queries"]
            lines += [
                "",
                f"Secrets disclosed in words ({dc['rows']} probes = {len(set(dc.get('now_leaking_templates', [])))} "
                "templates still leaking now; synthetic shapeless secrets after a credential noun, "
                "templates written together with the pattern, so not blind): distinctive secret "
                "words left in trace-bound fields.",
                "",
                "| redaction | rows leaking | secret words leaked |",
                "|---|---:|---:|",
                f"| none (raw) | {dc['raw_rows']} | {dc['raw_words']} / {dc['n_words_total']} |",
                f"| PR #15 patterns | {dc['pr15_rows']} | {dc['pr15_words']} / {dc['n_words_total']} |",
                f"| now (+ disclosed-secret pattern) | {dc['now_rows']} | {dc['now_words']} / {dc['n_words_total']} |",
                "",
                f"Over-redaction cost: trace `query` changed by the new pattern on {ov['golden']} golden, "
                f"{ov['perturbed']} perturbed and {ov['write']} write-refusal rows.",
            ]
            lg, st = dc.get("login"), dc.get("states")
            if lg and st:
                lines += [
                    "",
                    f"Disclosed by purpose, no credential noun ({lg['rows']} probes, `use {{s}} to log in ...`): "
                    f"secret words leaked PR #16 {lg['pr16_words']} / {lg['n_words_total']} -> now "
                    f"{lg['now_words']} / {lg['n_words_total']} (rows {lg['pr16_rows']} -> {lg['now_rows']}).",
                    "",
                    f"Credential states that are not values ({st['n']} statements such as `the vault token is "
                    f"expired`): trace `query` redacted PR #16 {st['pr16_redacted']} -> now {st['now_redacted']}"
                    + (f" ({'; '.join(st['now_redacted_examples'])})" if st["now_redacted_examples"] else "")
                    + ".",
                ]
        rt = r.get("random_tokens")
        if rt:
            ov = rt["over_redacted_queries"]
            tot = rt["total"]
            lines += [
                "",
                f"Random tokens with no format and no credential cue ({tot['rows']} probes: seeded synthetic "
                "secrets of every `secret_entropy` family x 5 templates; written with the detector, so not "
                "blind): rows whose trace-bound fields still hold the secret string. The PR #16 column "
                "re-redacts the boundary fields only (explanations are redacted when built).",
                "",
                "| family | rows | none (raw) | PR #16 patterns | now (+ random-token detector) |",
                "|---|---:|---:|---:|---:|",
            ]
            for fam, t in rt["by_family"].items():
                tag = " (not gating)" if fam in rt["ungated_families"] else ""
                lines.append(f"| {fam}{tag} | {t['rows']} | {t['raw']} | {t['pr16']} | {t['now']} |")
            lines += [
                f"| **all** | {tot['rows']} | {tot['raw']} | {tot['pr16']} | {tot['now']} |",
                "",
                f"Over-redaction cost: trace `query` changed by the detector on {ov['golden']} golden, "
                f"{ov['perturbed']} perturbed and {ov['write']} write-refusal rows.",
            ]
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
        bad += r["disclosure"]["now_words"]
        bad += r["disclosure"]["login"]["now_words"]
        bad += r["random_tokens"]["gated_now"]
        rt = r["random_tokens"]
        print(
            f"{'':30s} random-token probe rows leaking: raw={rt['total']['raw']} "
            f"pr16={rt['total']['pr16']} now={rt['total']['now']} (of {rt['total']['rows']}; "
            f"gating {rt['gated_now']}); over-redacted queries {rt['over_redacted_queries']}"
        )
        print(
            f"{'':30s} disclosed-in-words secret words leaked: raw={r['disclosure']['raw_words']} "
            f"pr15={r['disclosure']['pr15_words']} now={r['disclosure']['now_words']} "
            f"(of {r['disclosure']['n_words_total']}); over-redacted queries "
            f"{r['disclosure']['over_redacted_queries']}"
        )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
