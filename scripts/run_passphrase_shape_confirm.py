"""One-shot confirm of the Nov 1 shape-guard pick (pre-registered in ``passphrase_shape_protocol``).

    python scripts/run_passphrase_shape_confirm.py --raw-dir /tmp/se_qa_raw

Scores the shipped detector and the calibration pick (read from the committed
calibration artifact) on the confirm seeds and the Stack Exchange *test* split,
plus the off-list control (reported only). Writes
``artifacts/passphrase_shape_confirm.{json,md}``. The confirm seeds are spent once
this has run.
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
from ops_copilot.passphrase_wordlist import offlist_words, score_rows, wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path) -> dict:
    chosen = json.loads((ART / "passphrase_shape_calibration.json").read_text())["chosen"]
    arm = next(a for a in S.arms() if S.arm_name(a) == chosen)
    out = run_phase(S.CONFIRM_SEEDS, "test", raw_dir, [S.SHIPPED, arm])
    base, res = out["results"]
    res["checks"] = S.confirm_passes(res, base)
    base["checks"] = {}
    out["chosen"] = chosen
    out["ships"] = all(res["checks"].values())
    off = wordlist_passphrases(S.OFFLIST_SEED, S.N_ROWS, words=offlist_words())
    out["offlist"] = {"seed": S.OFFLIST_SEED, **{S.arm_name(a): score_rows(off, S.patterns_for(a))["total"] for a in (S.SHIPPED, arm)}}
    return out


def render(out: dict) -> str:
    s = out["seeds"]
    base, res = out["results"]
    lines = [
        f"# Passphrase shape guards: one-shot confirm (seeds {' / '.join(str(s[k]) for k in S.PROBES)}, "
        f"{out['rows']:,} rows each; {out['se_sentences']:,} SE test sentences, {out['se_identifiers']:,} SE test identifiers)",
        "",
        f"Pick from calibration: `{out['chosen']}`. Never scored on these seeds or on SE test before this run.",
        "",
        *table(out["results"], "checks"),
        "",
        "Checks: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in res["checks"].items()),
        "",
        f"**{'Ships on.' if out['ships'] else 'Ships off.'}** The confirm seeds are spent.",
        "",
        f"SE test identifiers flagged: {base['se']['ident_flagged']} -> {res['se']['ident_flagged']} of {out['se_identifiers']} "
        f"(no longer flagged: {', '.join(f'`{x}`' for x in res['se']['ident_unflagged_examples']) or 'none'}).",
        "",
        "Rows leaking, shipped -> pick: " + "; ".join(
            f"{k} {base['probe'][k]['total']['leak_rows']} -> {res['probe'][k]['total']['leak_rows']}" for k in S.PROBES),
        "",
        f"Off-list control (seed {out['offlist']['seed']}, reported only): leaked words "
        + " -> ".join(str(out["offlist"][a]["leak_words"]) for a in (base["arm"], res["arm"]))
        + f" of {out['offlist'][base['arm']]['words']:,}.",
    ]
    if res["se"]["ident_new_examples"]:
        lines += ["", "New SE test identifier flags: " + ", ".join(f"`{x}`" for x in res["se"]["ident_new_examples"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_shape_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_shape_confirm.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
