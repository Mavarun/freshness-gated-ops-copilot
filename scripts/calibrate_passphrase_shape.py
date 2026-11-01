"""Calibrate the Nov 1 shape guards (pre-registered in ``passphrase_shape_protocol``).

    python scripts/calibrate_passphrase_shape.py --raw-dir /tmp/se_qa_raw

Scores all 8 arms on the calibration seeds (five probes, 1,200 rows each) and the
Stack Exchange *train* sentences and identifiers, applies the eight safety checks
and the pick rule, and writes ``artifacts/passphrase_shape_calibration.{json,md}``.
Needs the raw QA pages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_shape_protocol as S  # noqa: E402
from ops_copilot.passphrase_shape_eval import run_phase, table  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path) -> dict:
    out = run_phase(S.CALIB_SEEDS, "train", raw_dir, S.arms())
    base = out["results"][0]
    for r in out["results"]:
        r["safe"] = S.is_safe(r, base)
    chosen = S.pick(out["results"], base)
    out["chosen"] = chosen["arm"] if chosen else None
    return out


def render(out: dict) -> str:
    s = out["seeds"]
    base = out["results"][0]
    lines = [
        f"# Passphrase shape guards: calibration (seeds {' / '.join(str(s[k]) for k in S.PROBES)}, "
        f"{out['rows']:,} rows each; {out['se_sentences']:,} SE train sentences, {out['se_identifiers']:,} SE train identifiers)",
        "",
        "Pre-registered in `ops_copilot.passphrase_shape_protocol`. `shipped` is the Oct 31 detector. Probe words: "
        + ", ".join(f"{k} {base['probe'][k]['total']['words']:,}" for k in S.PROBES) + ".",
        "",
        *table(out["results"]),
        "",
        f"**Chosen:** `{out['chosen']}`" if out["chosen"] else "**No arm is safe.**",
    ]
    for r in out["results"]:
        if r["arm"] == out["chosen"] and r["arm"] != "shipped":
            se = r["se"]
            lines += [
                "",
                f"SE train identifiers no longer flagged: {se['ident_unflagged']} "
                f"(by guard, a name can hit several: {', '.join(f'{g} {n}' for g, n in se['ident_unflagged_by_guard'].items())}). "
                "Examples: " + ", ".join(f"`{x}`" for x in se["ident_unflagged_examples"][:8]),
                "",
                "Still flagged (first few): " + ", ".join(f"`{x}`" for x in se["ident_still_flagged_examples"][:8]),
                "",
                "Leak causes, chosen: " + "; ".join(
                    f"{k}: " + (", ".join(f"{c} {v}" for c, v in r["probe"][k]["cause"].items()) or "none") for k in S.PROBES),
            ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    ART.mkdir(exist_ok=True)
    (ART / "passphrase_shape_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_shape_calibration.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
