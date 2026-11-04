"""The Nov 4 space-bridge protocol (pre-registered in ``passphrase_space_protocol``).

    python scripts/run_passphrase_space_protocol.py --phase calibrate --raw-dir /tmp/se_qa_raw
    python scripts/run_passphrase_space_protocol.py --phase confirm --raw-dir /tmp/se_qa_raw   # one shot

``calibrate`` scores all five arms on the calibration seeds and SE *train* and records the pick;
``confirm`` runs only if the committed calibration artifact has a pick, scores shipped and the pick on
the confirm seeds and SE *test*, and the confirm seeds are spent once it has run.
Writes ``artifacts/passphrase_space_{calibration,confirm}.{json,md}``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_space_protocol as F  # noqa: E402
from ops_copilot.passphrase_shape_eval import run_phase  # noqa: E402

ART = ROOT / "artifacts"
BY_NAME = {F.arm_name(a): a for a in F.arms()}


def run(phase: str, raw_dir: Path) -> dict:
    if phase == "confirm":
        cal = json.loads((ART / "passphrase_space_calibration.json").read_text())
        if not cal["pick"]:
            raise SystemExit("calibration found no safe arm with a gain; the protocol stops before the confirm")
        arms = [F.SHIPPED, BY_NAME[cal["pick"]]]
        seeds, split = F.CONFIRM_SEEDS, "test"
    else:
        arms, seeds, split = F.arms(), F.CALIB_SEEDS, "train"
    out = run_phase(seeds, split, raw_dir, arms, proto=F)
    base, *rest = out["results"]
    base["checks"] = {}
    fn = F.calibration_passes if phase == "calibrate" else F.confirm_passes
    for r in rest:
        r["checks"] = fn(r, base)
    out["phase"] = phase
    if phase == "calibrate":
        chosen = F.pick(rest, base)
        out["pick"] = chosen["arm"] if chosen else None
        out["passes"] = chosen is not None
    else:
        out["pick"] = rest[0]["arm"]
        out["passes"] = all(rest[0]["checks"].values())
    return out


def _table(out: dict) -> list[str]:
    lines = [
        "| arm | leak words std / glued / invented / cased / phrase / connective (total) | over words | SE sentences flagged "
        "| SE ids flagged (new) | Oct 13 / queries / data ids | checks |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in out["results"]:
        lw = [r["probe"][k]["total"]["leak_words"] for k in F.PROBES]
        ov = sum(r["probe"][k]["total"]["over_words"] for k in F.PROBES)
        chk = r.get("checks", {})
        ok = "baseline" if not chk else ("yes" if all(chk.values()) else "no: " + ", ".join(k for k, v in chk.items() if not v))
        lines.append(
            f"| {r['arm']} | {' / '.join(map(str, lw))} ({sum(lw)}) | {ov} | {r['se']['sent_flagged']} | "
            f"{r['se']['ident_flagged']} ({r['se']['ident_new']}) | {r['oct13_leak_words']} / {r['repo_query_changes']} / "
            f"{len(r['data_ident_new_flags'])} | {ok} |"
        )
    return lines


def render(out: dict) -> str:
    s, base = out["seeds"], out["results"][0]
    split = "train" if out["phase"] == "calibrate" else "test"
    if out["phase"] == "calibrate":
        verdict = (f"Pick: `{out['pick']}`. It goes to the one-shot confirm." if out["pick"]
                   else "No arm is safe with a gain: the knob stays off and the confirm seeds stay unspent.")
    else:
        verdict = (f"**`{out['pick']}` ships on.** The confirm seeds are spent." if out["passes"]
                   else f"**`{out['pick']}` ships off.** The confirm seeds are spent.")
    lines = [
        f"# Space-joined function words: {out['phase']} (seeds {' / '.join(str(s[k]) for k in F.PROBES)}, "
        f"{out['rows']:,} rows each; {out['se_sentences']:,} SE {split} sentences, {out['se_identifiers']:,} SE {split} identifiers)",
        "",
        "Pre-registered in `ops_copilot.passphrase_space_protocol`. `shipped` is the Nov 1 detector (function parts on, no space bridge).",
        "Arms are `bridge list / max bridge words`.",
        "",
        *_table(out),
        "",
    ]
    for r in out["results"][1:]:
        lines.append(f"Checks `{r['arm']}`: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in r["checks"].items()))
    lines += ["", verdict, ""]
    for k in ("phrase", "connective"):
        pb = base["probe"][k]
        for r in out["results"][1:]:
            pr = r["probe"][k]
            lines.append(f"{k} probe by separator, leaked words shipped -> `{r['arm']}`: " + "; ".join(
                f"{x} {pb['by_separator'][x]['leak_words']} -> {pr['by_separator'][x]['leak_words']}" for x in sorted(pb["by_separator"])))
    for r in out["results"][1:]:
        if r["se"]["ident_new_examples"]:
            lines.append(f"New SE {split} identifier flags (`{r['arm']}`): " + ", ".join(f"`{x}`" for x in r["se"]["ident_new_examples"]))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    ap.add_argument("--raw-dir", type=Path, required=True)
    a = ap.parse_args()
    out = run(a.phase, a.raw_dir)
    name = "calibration" if a.phase == "calibrate" else "confirm"
    ART.mkdir(exist_ok=True)
    (ART / f"passphrase_space_{name}.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / f"passphrase_space_{name}.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
