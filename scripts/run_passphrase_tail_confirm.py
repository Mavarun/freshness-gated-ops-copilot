"""One-shot confirm of the calibrated passphrase arm (``passphrase_tail_protocol``).

    python scripts/run_passphrase_tail_confirm.py --raw-dir /tmp/se_qa_raw

Scores the shipped detector and the calibration pick on the confirm seed and the
Stack Exchange *test* sentences, applies the pre-registered ship rule and writes
``artifacts/passphrase_tail_confirm.{json,md}``. The confirm seed is spent by the
first run; re-running reproduces the same numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_tail_protocol as P  # noqa: E402
from ops_copilot.passphrase_wordlist import wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"


def _parse(name: str):
    t, c = name.split("/")
    return (t, None if c == "none" else float(c))


def run(raw_dir: Path) -> dict:
    cal = json.loads((ART / "passphrase_tail_calibration.json").read_text())
    chosen = _parse(cal["chosen"])
    rows = wordlist_passphrases(P.CONFIRM_SEED, P.N_ROWS)
    se = P.se_candidates(raw_dir)["test"]
    base_q = P.shipped_repo_queries()
    base = P.evaluate_arm(P.SHIPPED, rows, se, base_queries=base_q)
    pick = P.evaluate_arm(chosen, rows, se, base_queries=base_q)
    checks = P.is_safe(pick, base, fp_budget=P.FP_BUDGET_TEST)
    checks["fewer_leaked_words"] = pick["probe"]["total"]["leak_words"] < base["probe"]["total"]["leak_words"]
    return {
        "seed": P.CONFIRM_SEED,
        "rows": P.N_ROWS,
        "se_test_candidates": len(se),
        "shipped": base,
        "chosen": pick,
        "checks": checks,
        "ships_on": all(checks.values()),
    }


def render(out: dict) -> str:
    b, c = out["shipped"], out["chosen"]
    bt, ct = b["probe"]["total"], c["probe"]["total"]
    lines = [
        f"# Passphrase tail / incoherence arm: one-shot confirm (seed {out['seed']}, {out['rows']} EFF rows; "
        f"{out['se_test_candidates']} Stack Exchange test sentences)",
        "",
        "| | shipped (`trim/none`) | chosen (`%s`) |" % c["arm"],
        "| :--- | ---: | ---: |",
        f"| rows leaking a passphrase word | {bt['leak_rows']} / {bt['rows']} | {ct['leak_rows']} / {ct['rows']} |",
        f"| passphrase words leaked | {bt['leak_words']} / {bt['words']} | {ct['leak_words']} / {ct['words']} |",
        f"| template words over-redacted | {bt['over_words']} | {ct['over_words']} |",
        f"| SE test sentences flagged (all false positives) | {b['se']['flagged']} | {c['se']['flagged']} |",
        f"| Oct 13 probe words leaked | {b['oct13_leak_words']} | {c['oct13_leak_words']} |",
        f"| golden / perturbed / write trace queries changed | - | {c['repo_query_changes']} |",
        "",
        "Leak causes: shipped " + ", ".join(f"{k} {v}" for k, v in b["probe"]["cause"].items())
        + "; chosen " + ", ".join(f"{k} {v}" for k, v in c["probe"]["cause"].items()),
        "",
        "By separator (leak words, shipped -> chosen): "
        + ", ".join(f"{s} {b['probe']['by_separator'][s]['leak_words']} -> {c['probe']['by_separator'][s]['leak_words']}" for s in b["probe"]["by_separator"]),
        "",
        "Checks: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in out["checks"].items()),
        "",
        f"**Ships {'on' if out['ships_on'] else 'off'}.**",
        "",
        "Rows the chosen arm still leaks (first few):",
        "",
    ]
    lines += [f"- {e['cause']}: `{e['text']}` leaks {', '.join(e['leaked'])}" for e in c["probe"]["examples"][:6]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_tail_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_tail_confirm.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
