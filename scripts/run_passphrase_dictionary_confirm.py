"""One-shot confirm of the Oct 31 pick (pre-registered in ``passphrase_dictionary_protocol``).

    python scripts/run_passphrase_dictionary_confirm.py --raw-dir /tmp/se_qa_raw

Scores the shipped detector and the calibration pick (read from the committed
calibration artifact) on the confirm seeds and the Stack Exchange *test* split,
plus the off-list control (reported only). Writes
``artifacts/passphrase_dictionary_confirm.{json,md}``. The confirm seeds are spent
once this has run.
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
from ops_copilot.passphrase_wordlist import offlist_words, score_rows, wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path) -> dict:
    chosen = json.loads((ART / "passphrase_dictionary_calibration.json").read_text())["chosen"]
    arm = next(a for a in P.arms() if P.arm_name(a) == chosen)
    out = run_phase(P.confirm_seeds(), "test", raw_dir, [P.SHIPPED, arm])
    base, res = out["results"]
    res["checks"] = P.confirm_passes(res, base)
    base["checks"] = {}
    out["chosen"] = chosen
    out["ships"] = all(res["checks"].values())
    off = wordlist_passphrases(P.OFFLIST_SEED, P.N_ROWS, words=offlist_words())
    out["offlist"] = {"seed": P.OFFLIST_SEED, **{P.arm_name(a): score_rows(off, P.patterns_for(a))["total"] for a in (P.SHIPPED, arm)}}
    return out


def render(out: dict) -> str:
    s = out["seeds"]
    base, res = out["results"]
    lines = [
        f"# Passphrase dictionary / digit-guard: one-shot confirm (seeds {s['standard']} / {s['attached']} / {s['invented']}, "
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
        "Rows leaking, shipped -> pick: " + "; ".join(
            f"{k} {base['probe'][k]['total']['leak_rows']} -> {res['probe'][k]['total']['leak_rows']}" for k in P.PROBES),
        "",
        "Leak causes with the pick: " + "; ".join(
            f"{k}: " + (", ".join(f"{c} {v}" for c, v in res["probe"][k]["cause"].items()) or "none") for k in P.PROBES),
        "",
        f"Off-list control (seed {out['offlist']['seed']}, reported only): leaked words "
        + " -> ".join(str(out["offlist"][a]["leak_words"]) for a in (base["arm"], res["arm"]))
        + f" of {out['offlist'][base['arm']]['words']:,}.",
    ]
    if res["se"]["ident_new_examples"]:
        lines += ["", "New SE test identifier flags: " + ", ".join(f"`{x}`" for x in res["se"]["ident_new_examples"])]
    ex = res["probe"]["attached"]["examples"]
    if ex:
        lines += ["", "Glued-digit rows still leaking (first few):", ""] + [f"- `{e['text']}`" for e in ex[:6]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_dictionary_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_dictionary_confirm.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
