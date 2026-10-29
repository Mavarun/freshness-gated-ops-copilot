"""Calibrate the Oct 29 passphrase knobs (pre-registered in ``passphrase_tail_protocol``).

    python scripts/calibrate_passphrase_tail.py --raw-dir /tmp/se_qa_raw

Scores all 14 arms on the calibration seed and the Stack Exchange *train*
sentences, applies the safety checks and the pick rule, and writes
``artifacts/passphrase_tail_calibration.{json,md}``. Needs the raw QA pages
(not in CI); the committed artifact is pinned by a test.
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


def run(raw_dir: Path) -> dict:
    rows = wordlist_passphrases(P.CALIB_SEED, P.N_ROWS)
    se = P.se_candidates(raw_dir)["train"]
    base_q = P.shipped_repo_queries()
    results = [P.evaluate_arm(a, rows, se, base_queries=base_q) for a in P.arms()]
    base = results[0]
    for r in results:
        r["safe"] = P.is_safe(r, base, fp_budget=P.FP_BUDGET_TRAIN)
    chosen = P.pick(results, base)
    return {
        "seed": P.CALIB_SEED,
        "rows": P.N_ROWS,
        "se_train_candidates": len(se),
        "results": results,
        "chosen": chosen["arm"] if chosen else None,
    }


def render(out: dict) -> str:
    lines = [
        "# Passphrase tail / incoherence arms: calibration (seed %d, %d EFF rows; %s Stack Exchange train sentences)"
        % (out["seed"], out["rows"], f"{out['se_train_candidates']:,}"),
        "",
        "Pre-registered in `ops_copilot.passphrase_tail_protocol`. Leaked = passphrase words (4+ letters) left in the "
        "redacted trace query. Over = template words redacted. SE flagged = train sentences with a flagged span "
        "(every flag is a false positive).",
        "",
        "| arm | leak rows | leak words | over words | SE flagged | Oct 13 leaks | repo query changes | safe |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in out["results"]:
        t = r["probe"]["total"]
        lines.append(
            f"| {r['arm']} | {t['leak_rows']} | {t['leak_words']} | {t['over_words']} | {r['se']['flagged']} | "
            f"{r['oct13_leak_words']} | {r['repo_query_changes']} | {'yes' if all(r['safe'].values()) else 'no'} |"
        )
    lines += ["", f"**Chosen:** `{out['chosen']}`" if out["chosen"] else "**No arm is safe.**", ""]
    base = out["results"][0]
    lines += ["Leak causes, shipped detector: " + ", ".join(f"{k} {v}" for k, v in base["probe"]["cause"].items()), ""]
    for r in out["results"]:
        if r["arm"] == out["chosen"]:
            lines += ["Leak causes, chosen arm: " + ", ".join(f"{k} {v}" for k, v in r["probe"]["cause"].items()), ""]
            extra = [e for e in r["se"]["examples"] if e not in base["se"]["examples"]]
            if extra:
                lines += ["New Stack Exchange train flags (first few):", ""] + [f"- {', '.join(f'`{h}`' for h in e)}" for e in extra[:6]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_tail_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_tail_calibration.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
