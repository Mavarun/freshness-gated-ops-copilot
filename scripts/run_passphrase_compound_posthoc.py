"""Post-hoc look at the Oct 30 ship (after the confirm; nothing here changes a default).

    python scripts/run_passphrase_compound_posthoc.py

Offline, ~20 s. Three questions, each on spent or new-but-diagnostic rows:

1. **Which knob does the work?** The eight arms without but1_4 / all3 on confirm
   seed 3037 and on the off-list control (3053).
2. **What still leaks?** Every leaking confirm row under the shipped patterns.
3. **Bitwarden-style numbers.** Bitwarden's generator glues one digit to a random
   word ("Ranch3") instead of adding a number part. The probe never drew that
   shape. Seed 3061 rows with ``number_style="attached"``, Oct 29 vs shipped.

Writes ``artifacts/passphrase_compound_posthoc.{json,md}``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_compound_protocol as C  # noqa: E402
from ops_copilot.explain_redact import SENSITIVE_PATTERNS  # noqa: E402
from ops_copilot.passphrase_wordlist import _present, offlist_words, redact_query, score_rows, wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"
ATTACHED_SEED = 3061


def run() -> dict:
    rows = wordlist_passphrases(C.CONFIRM_SEED, C.N_ROWS)
    off = wordlist_passphrases(C.OFFLIST_SEED, C.N_ROWS, words=offlist_words())
    arms = [a for a in C.arms() if a[0] in (None, "all4")]
    attribution = {
        C.arm_name(a): {"confirm": score_rows(rows, C.patterns_for(a))["total"], "offlist": score_rows(off, C.patterns_for(a))["total"]}
        for a in arms
    }
    leaks = []
    for r in rows:
        red = redact_query(r.text, SENSITIVE_PATTERNS).lower()
        lw = [w.lower() for w in r.words if len(w) >= 4 and _present(red, w.lower())]
        if lw:
            leaks.append({"text": r.text, "separator": r.separator, "leaked": lw})
    att = wordlist_passphrases(ATTACHED_SEED, C.N_ROWS, number_style="attached")
    attached = {
        "oct29": score_rows(att, C.patterns_for(C.SHIPPED)),
        "shipped": score_rows(att, SENSITIVE_PATTERNS),
    }
    return {"attribution": attribution, "confirm_leaks": leaks, "attached_seed": ATTACHED_SEED, "attached": attached}


def render(out: dict) -> str:
    lines = [
        "# Oct 30 passphrase ship: post-hoc (after the confirm)",
        "",
        "## Which knob does the work (leaked words of ~5,960 / 5,990)",
        "",
        "| arm | confirm seed 3037 | off-list control 3053 |",
        "| --- | ---: | ---: |",
    ]
    for k, v in out["attribution"].items():
        lines.append(f"| {k} | {v['confirm']['leak_words']} | {v['offlist']['leak_words']} |")
    lines += ["", f"## Confirm rows still leaking under the shipped patterns ({len(out['confirm_leaks'])})", ""]
    lines += [f"- `{x['text']}` -> {', '.join(x['leaked'])}" for x in out["confirm_leaks"]]
    a, b = out["attached"]["oct29"], out["attached"]["shipped"]
    lines += [
        "",
        f"## Bitwarden-style numbers (seed {out['attached_seed']}, one digit glued to a random word)",
        "",
        f"Rows leaking: Oct 29 {a['total']['leak_rows']} -> shipped {b['total']['leak_rows']} of {b['total']['rows']:,}; "
        f"words leaked {a['total']['leak_words']} -> {b['total']['leak_words']} of {b['total']['words']:,}.",
        "",
        "| separator | rows leaking (shipped) | words leaked (shipped) |",
        "| --- | ---: | ---: |",
    ]
    for sep, v in b["by_separator"].items():
        lines.append(f"| {sep} | {v['leak_rows']} / {v['rows']} | {v['leak_words']} |")
    lines += ["", "Examples (shipped):", ""] + [f"- `{e['text']}`" for e in b["examples"][:5]]
    return "\n".join(lines) + "\n"


def main() -> None:
    out = run()
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_compound_posthoc.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_compound_posthoc.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
