"""The Nov 1 function-parts protocol (pre-registered in ``passphrase_phrase_protocol``).

    python scripts/run_passphrase_phrase_protocol.py --phase calibrate --raw-dir /tmp/se_qa_raw
    python scripts/run_passphrase_phrase_protocol.py --phase confirm --raw-dir /tmp/se_qa_raw   # one shot

``calibrate`` scores the shipped detector and the knob on the calibration seeds and
SE *train*; ``confirm`` runs only if the committed calibration artifact passed, on
the confirm seeds and SE *test*, and the confirm seeds are spent once it has run.
Writes ``artifacts/passphrase_phrase_{calibration,confirm}.{json,md}``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_phrase_protocol as F  # noqa: E402
from ops_copilot.passphrase_shape_eval import run_phase, table  # noqa: E402

ART = ROOT / "artifacts"


def run(phase: str, raw_dir: Path) -> dict:
    if phase == "confirm":
        cal = json.loads((ART / "passphrase_phrase_calibration.json").read_text())
        if not cal["passes"]:
            raise SystemExit("calibration did not pass; the protocol stops before the confirm")
    seeds, split = (F.CALIB_SEEDS, "train") if phase == "calibrate" else (F.CONFIRM_SEEDS, "test")
    out = run_phase(seeds, split, raw_dir, F.arms(), proto=F)
    base, res = out["results"]
    fn = F.calibration_passes if phase == "calibrate" else F.confirm_passes
    res["checks"] = fn(res, base)
    base["checks"] = {}
    out["phase"] = phase
    out["passes"] = all(res["checks"].values())
    return out


def render(out: dict) -> str:
    s, base, res = out["seeds"], *out["results"]
    split = "train" if out["phase"] == "calibrate" else "test"
    pb, pr = base["probe"]["phrase"], res["probe"]["phrase"]
    verdict = ("Passes: goes to the one-shot confirm." if out["passes"] else "Fails: the protocol stops here.") \
        if out["phase"] == "calibrate" else ("**Ships on.** The confirm seeds are spent." if out["passes"]
                                             else "**Ships off.** The confirm seeds are spent.")
    lines = [
        f"# Function-word parts in compounds: {out['phase']} (seeds {' / '.join(str(s[k]) for k in F.PROBES)}, "
        f"{out['rows']:,} rows each; {out['se_sentences']:,} SE {split} sentences, {out['se_identifiers']:,} SE {split} identifiers)",
        "",
        "Pre-registered in `ops_copilot.passphrase_phrase_protocol`. `shipped` is the Nov 1 detector (shape guards on).",
        "",
        *table(out["results"], "checks"),
        "",
        "Checks: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in res["checks"].items()),
        "",
        verdict,
        "",
        "Phrase probe by separator, leaked words shipped -> knob: " + "; ".join(
            f"{k} {pb['by_separator'][k]['leak_words']} -> {pr['by_separator'][k]['leak_words']}" for k in sorted(pb["by_separator"])),
        "",
        "Phrase leak causes with the knob: " + (", ".join(f"{c} {v}" for c, v in pr["cause"].items()) or "none"),
    ]
    if res["se"]["ident_new_examples"]:
        lines += ["", f"New SE {split} identifier flags: " + ", ".join(f"`{x}`" for x in res["se"]["ident_new_examples"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    ap.add_argument("--raw-dir", type=Path, required=True)
    a = ap.parse_args()
    out = run(a.phase, a.raw_dir)
    name = "calibration" if a.phase == "calibrate" else "confirm"
    ART.mkdir(exist_ok=True)
    (ART / f"passphrase_phrase_{name}.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / f"passphrase_phrase_{name}.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
