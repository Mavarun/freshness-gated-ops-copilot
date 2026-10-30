"""CI report: the shipped passphrase detector on real EFF diceware rows (offline, ~10 s).

    python scripts/run_passphrase_wordlist_eval.py

Scores the shipped patterns, the Oct 29 patterns (amended arm, Oct 29 purpose
pattern) and the Oct 13 detector (``tail="trim"``, no incoherence arm) on the
five spent seeds of the Oct 29 and Oct 30 protocols (2910, 2929, 2931, 3010,
3037) and on the Oct 30 off-list control rows (3053). Writes
``artifacts/passphrase_wordlist_eval.{json,md}``. Exits non-zero if, on any
seed or the control, the shipped patterns leak more passphrase words than the
Oct 29 ones (or the Oct 29 ones more than Oct 13), if any Oct 13 probe word
leaks, if any golden / perturbed / write trace query differs from the Oct 13
detector's, or if a ``data/`` identifier is newly flagged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_compound_protocol as C  # noqa: E402
from ops_copilot import passphrase_tail_protocol as P  # noqa: E402
from ops_copilot.explain_redact import SENSITIVE_PATTERNS  # noqa: E402
from ops_copilot.passphrase import CUED_PASSPHRASE  # noqa: E402
from ops_copilot.passphrase_wordlist import (  # noqa: E402
    _present,
    offlist_words,
    redact_query,
    score_rows,
    wordlist_passphrases,
)

ART = ROOT / "artifacts"
SEEDS = (P.CALIB_SEED, P.CONFIRM_SEED, P.AMENDED_CONFIRM_SEED, C.CALIB_SEED, C.CONFIRM_SEED)


def run() -> dict:
    old, mid = P.patterns_for(P.SHIPPED), C.patterns_for(C.SHIPPED)
    out: dict = {"seeds": {}, "failures": []}
    sources = [(str(s), wordlist_passphrases(s, P.N_ROWS)) for s in SEEDS]
    sources.append((f"offlist-{C.OFFLIST_SEED}", wordlist_passphrases(C.OFFLIST_SEED, C.N_ROWS, words=offlist_words())))
    for name, rows in sources:
        a, m, b = score_rows(rows, old)["total"], score_rows(rows, mid)["total"], score_rows(rows, SENSITIVE_PATTERNS)
        out["seeds"][name] = {"oct13": a, "oct29": m, "shipped": b["total"], "shipped_cause": b["cause"]}
        if b["total"]["leak_words"] > m["leak_words"]:
            out["failures"].append(f"{name}: shipped leaks more words than Oct 29")
        if m["leak_words"] > a["leak_words"]:
            out["failures"].append(f"{name}: Oct 29 leaks more words than Oct 13")
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
        "Every seed was spent by the Oct 29 or Oct 30 protocol, so this is a regression report, not a fresh test. "
        "`offlist-3053` is the Oct 30 control: the same rows built from WordNet nouns that are not on the EFF list.",
        "",
        "| seed | rows leaking (Oct 13 -> Oct 29 -> shipped) | words leaked (Oct 13 -> Oct 29 -> shipped) | over-redacted template words |",
        "| --- | ---: | ---: | ---: |",
    ]
    for s, v in out["seeds"].items():
        a, m, b = v["oct13"], v["oct29"], v["shipped"]
        lines.append(
            f"| {s} | {a['leak_rows']} -> {m['leak_rows']} -> {b['leak_rows']} | {a['leak_words']} -> {m['leak_words']} -> "
            f"{b['leak_words']} of {a['words']} | {a['over_words']} -> {m['over_words']} -> {b['over_words']} |"
        )
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
