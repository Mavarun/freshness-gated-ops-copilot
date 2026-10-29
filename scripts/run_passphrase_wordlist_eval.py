"""CI report: the shipped passphrase detector on real EFF diceware rows (offline, ~10 s).

    python scripts/run_passphrase_wordlist_eval.py

Scores the shipped patterns and the Oct 13 detector (``tail="trim"``, no
incoherence arm) on the three spent seeds of the Oct 29 protocol (calibration
2910, first confirm 2929, amended confirm 2931). Writes
``artifacts/passphrase_wordlist_eval.{json,md}``. Exits non-zero if, on any
seed, the shipped patterns leak more passphrase words than the Oct 13 detector,
if any Oct 13 probe word leaks, if any golden / perturbed / write trace query
differs from the Oct 13 detector's, or if a ``data/`` identifier is newly flagged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_tail_protocol as P  # noqa: E402
from ops_copilot.explain_redact import SENSITIVE_PATTERNS  # noqa: E402
from ops_copilot.passphrase import CUED_PASSPHRASE  # noqa: E402
from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows, wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"
SEEDS = (P.CALIB_SEED, P.CONFIRM_SEED, P.AMENDED_CONFIRM_SEED)


def run() -> dict:
    old = P.patterns_for(P.SHIPPED)
    out: dict = {"seeds": {}, "failures": []}
    for seed in SEEDS:
        rows = wordlist_passphrases(seed, P.N_ROWS)
        a, b = score_rows(rows, old)["total"], score_rows(rows, SENSITIVE_PATTERNS)
        out["seeds"][str(seed)] = {"oct13": a, "shipped": b["total"], "shipped_cause": b["cause"]}
        if b["total"]["leak_words"] > a["leak_words"]:
            out["failures"].append(f"seed {seed}: shipped leaks more words than Oct 13")
    out["oct13_probe_leak_words"] = sum(
        sum(_present(redact_query(t, SENSITIVE_PATTERNS).lower(), w) for w in ws) for t, ws in P.oct13_probe_texts()
    )
    base_q = P.shipped_repo_queries()
    out["repo_query_changes"] = sum(redact_query(q, SENSITIVE_PATTERNS) != red for q, red in base_q.items())
    base_ids = set(P.identifier_flags(P.SHIPPED))
    out["new_identifier_flags"] = sorted(
        f"{c} {n}" for n in P.data_identifiers() for c in P.IDENTIFIER_CUES
        if CUED_PASSPHRASE.search(f"{c} {n}") and f"{c} {n}" not in base_ids
    )
    if out["oct13_probe_leak_words"]:
        out["failures"].append("Oct 13 probe leaks")
    if out["repo_query_changes"]:
        out["failures"].append("golden/perturbed/write trace queries changed")
    if out["new_identifier_flags"]:
        out["failures"].append("data/ identifiers newly flagged")
    return out


def render(out: dict) -> str:
    lines = [
        "# Passphrases from the EFF large wordlist: shipped detector vs Oct 13",
        "",
        "1,200 seeded rows per seed (4-6 EFF words, four separators, half Title-Case + number, five templates). "
        "All three seeds were spent by the Oct 29 protocol, so this is a regression report, not a fresh test.",
        "",
        "| seed | rows leaking (Oct 13 -> shipped) | words leaked (Oct 13 -> shipped) | over-redacted template words |",
        "| --- | ---: | ---: | ---: |",
    ]
    for s, v in out["seeds"].items():
        a, b = v["oct13"], v["shipped"]
        lines.append(f"| {s} | {a['leak_rows']} -> {b['leak_rows']} | {a['leak_words']} -> {b['leak_words']} of {a['words']} | {a['over_words']} -> {b['over_words']} |")
    lines += [
        "",
        f"Oct 13 probe words leaked: {out['oct13_probe_leak_words']}. Trace queries changed: {out['repo_query_changes']}. "
        f"New identifier flags: {len(out['new_identifier_flags'])}.",
        "",
        "Failures: " + ("none" if not out["failures"] else "; ".join(out["failures"])),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    out = run()
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_wordlist_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_wordlist_eval.md").write_text(render(out))
    print(render(out))
    return 1 if out["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
