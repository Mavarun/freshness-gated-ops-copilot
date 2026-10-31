"""Calibrate the Oct 31 passphrase knobs (pre-registered in ``passphrase_dictionary_protocol``).

    python scripts/calibrate_passphrase_dictionary.py --raw-dir /tmp/se_qa_raw

Scores all 15 arms on the calibration seeds (Oct 29-shape, Bitwarden glued-digit and
invented-word rows, 1,200 each) and the Stack Exchange *train* sentences and
identifiers, applies the eight safety checks and the pick rule, and writes
``artifacts/passphrase_dictionary_calibration.{json,md}``. Needs the raw QA pages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_dictionary_protocol as P  # noqa: E402
from ops_copilot.passphrase_dictionary_eval import run_phase, table  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path) -> dict:
    out = run_phase(P.calib_seeds(), "train", raw_dir, P.arms())
    base = out["results"][0]
    for r in out["results"]:
        r["safe"] = P.is_safe(r, base, fp_budget=P.FP_BUDGET_TRAIN, ident_budget=P.IDENT_BUDGET_TRAIN)
    chosen = P.pick(out["results"], base)
    out["chosen"] = chosen["arm"] if chosen else None
    return out


def render(out: dict) -> str:
    s = out["seeds"]
    base = out["results"][0]
    lines = [
        f"# Passphrase dictionary / digit-guard arms: calibration (seeds {s['standard']} / {s['attached']} / {s['invented']}, "
        f"{out['rows']:,} rows each; {out['se_sentences']:,} SE train sentences, {out['se_identifiers']:,} SE train identifiers)",
        "",
        "Pre-registered in `ops_copilot.passphrase_dictionary_protocol`. Arm = plain rule / scope / glued digit. "
        "`ops/compounds/off` is the shipped detector. Probe words: "
        + ", ".join(f"{k} {base['probe'][k]['total']['words']:,}" for k in P.PROBES) + ".",
        "",
        *table(out["results"]),
        "",
        f"**Chosen:** `{out['chosen']}`" if out["chosen"] else "**No arm is safe.**",
    ]
    for r in out["results"]:
        if r["arm"] == out["chosen"]:
            lines += ["", "Leak causes, chosen: " + "; ".join(
                f"{k}: " + ", ".join(f"{c} {v}" for c, v in r["probe"][k]["cause"].items()) for k in P.PROBES)]
            if r["se"]["ident_new_examples"]:
                lines += ["", "New SE train identifier flags: " + ", ".join(f"`{x}`" for x in r["se"]["ident_new_examples"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_dictionary_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_dictionary_calibration.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
