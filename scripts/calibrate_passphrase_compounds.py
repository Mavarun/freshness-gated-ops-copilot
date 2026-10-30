"""Calibrate the Oct 30 passphrase knobs (pre-registered in ``passphrase_compound_protocol``).

    python scripts/calibrate_passphrase_compounds.py --raw-dir /tmp/se_qa_raw

Scores all 16 arms on calibration seed 3010 (1,200 EFF rows), the Stack Exchange
*train* sentences and the Stack Exchange *train* identifiers, applies the six
safety checks and the pick rule, and writes
``artifacts/passphrase_compound_calibration.{json,md}``. Needs the raw QA pages
(not in CI); the committed artifact is pinned by a test.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_compound_protocol as P  # noqa: E402
from ops_copilot import passphrase_tail_protocol as T  # noqa: E402
from ops_copilot.passphrase_identifiers import identifier_flags, se_identifiers  # noqa: E402
from ops_copilot.passphrase_wordlist import wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"


def run_split(seed: int, split: str, raw_dir: Path, arms) -> dict:
    rows = wordlist_passphrases(seed, P.N_ROWS)
    se = T.se_candidates(raw_dir)[split]
    ids = se_identifiers(raw_dir)[split]
    base_q = P.shipped_repo_queries()
    base_ids = set(identifier_flags(P.detector(P.SHIPPED), ids))
    results = [P.evaluate_arm(a, rows, se, ids, base_queries=base_q, base_ident_flags=base_ids) for a in arms]
    return {"seed": seed, "rows": P.N_ROWS, "se_sentences": len(se), "se_identifiers": len(ids),
            "shipped_identifier_flags": len(base_ids), "results": results}


def run(raw_dir: Path) -> dict:
    out = run_split(P.CALIB_SEED, "train", raw_dir, P.arms())
    base = out["results"][0]
    for r in out["results"]:
        r["safe"] = P.is_safe(r, base, fp_budget=P.FP_BUDGET_TRAIN, ident_budget=P.IDENT_BUDGET_TRAIN)
    chosen = P.pick(out["results"], base)
    out["chosen"] = chosen["arm"] if chosen else None
    return out


def table(results: list[dict], base: dict) -> list[str]:
    lines = [
        "| arm | leak rows | leak words | over words | SE sentences flagged | SE identifiers newly flagged | Oct 13 leaks | repo query changes | data/ ids new | safe |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in results:
        t = r["probe"]["total"]
        safe = "yes" if all(r.get("safe", {"x": True}).values()) else "no: " + ", ".join(k for k, v in r["safe"].items() if not v)
        lines.append(
            f"| {r['arm']} | {t['leak_rows']} | {t['leak_words']} | {t['over_words']} | {r['se']['flagged']} | "
            f"{r['idents']['new_flags']} | {r['oct13_leak_words']} | {r['repo_query_changes']} | {len(r['data_ident_new_flags'])} | {safe} |"
        )
    return lines


def render(out: dict) -> str:
    base = out["results"][0]
    lines = [
        f"# Passphrase list / purpose arms: calibration (seed {out['seed']}, {out['rows']:,} EFF rows; "
        f"{out['se_sentences']:,} SE train sentences, {out['se_identifiers']:,} SE train identifiers)",
        "",
        "Pre-registered in `ops_copilot.passphrase_compound_protocol`. Arm = compound list mode / space list arm / "
        "purpose trailing number. `none/-/-` is the shipped detector. The shipped detector already flags "
        f"{out['shipped_identifier_flags']} of the {out['se_identifiers']:,} train identifiers; the identifier column counts flags on top of those.",
        "",
        *table(out["results"], base),
        "",
        f"**Chosen:** `{out['chosen']}`" if out["chosen"] else "**No arm is safe.**",
        "",
        "Leak causes, shipped: " + ", ".join(f"{k} {v}" for k, v in base["probe"]["cause"].items()),
    ]
    for r in out["results"]:
        if r["arm"] == out["chosen"]:
            lines += ["", "Leak causes, chosen: " + ", ".join(f"{k} {v}" for k, v in r["probe"]["cause"].items())]
            if r["idents"]["new_examples"]:
                lines += ["", "New SE train identifier flags: " + ", ".join(f"`{x}`" for x in r["idents"]["new_examples"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_compound_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_compound_calibration.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
