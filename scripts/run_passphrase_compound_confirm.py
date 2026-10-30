"""One-shot confirm of the Oct 30 pick (pre-registered in ``passphrase_compound_protocol``).

    python scripts/run_passphrase_compound_confirm.py --raw-dir /tmp/se_qa_raw

Scores the shipped detector and the calibration pick on confirm seed 3037
(1,200 EFF rows), the Stack Exchange *test* sentences and the Stack Exchange
*test* identifiers, applies the confirm rule, and also reports both on the
off-list control rows (seed 3053, not gating). Writes
``artifacts/passphrase_compound_confirm.{json,md}``. The seed is spent once this
has run; the committed artifact is pinned by a test.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_compound_protocol as P  # noqa: E402
from ops_copilot.passphrase_wordlist import offlist_words, score_rows, wordlist_passphrases  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from calibrate_passphrase_compounds import run_split, table  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path) -> dict:
    cal = json.loads((ART / "passphrase_compound_calibration.json").read_text())
    chosen = next(a for a in P.arms() if P.arm_name(a) == cal["chosen"])
    out = run_split(P.CONFIRM_SEED, "test", raw_dir, [P.SHIPPED, chosen])
    base, res = out["results"]
    res["confirm"] = P.confirm_passes(res, base)
    out["chosen"] = cal["chosen"]
    out["ships"] = all(res["confirm"].values())
    off = wordlist_passphrases(P.OFFLIST_SEED, P.N_ROWS, words=offlist_words())
    out["offlist"] = {P.arm_name(a): score_rows(off, P.patterns_for(a))["total"] for a in (P.SHIPPED, chosen)}
    return out


def render(out: dict) -> str:
    base, res = out["results"]
    off = out["offlist"]
    b, c = off["none/-/-"], off[out["chosen"]]
    lines = [
        f"# Passphrase list / purpose arms: one-shot confirm (seed {out['seed']}, {out['rows']:,} EFF rows; "
        f"{out['se_sentences']:,} SE test sentences, {out['se_identifiers']:,} SE test identifiers)",
        "",
        f"Pick from calibration: `{out['chosen']}`. The shipped detector already flags {out['shipped_identifier_flags']} "
        f"of the {out['se_identifiers']:,} test identifiers.",
        "",
        *table(out["results"], base),
        "",
        "Confirm checks: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in res["confirm"].items()),
        "",
        f"**{'Ships on.' if out['ships'] else 'Ships off.'}** Seed {out['seed']} is spent.",
        "",
        "Leak causes, shipped: " + ", ".join(f"{k} {v}" for k, v in base["probe"]["cause"].items()),
        "",
        "Leak causes, pick: " + ", ".join(f"{k} {v}" for k, v in res["probe"]["cause"].items()),
        "",
        f"Off-list control (seed {P.OFFLIST_SEED}, WordNet nouns not on the EFF list; reported, not gating): "
        f"leak words {b['leak_words']} -> {c['leak_words']} of {b['words']}, leak rows {b['leak_rows']} -> {c['leak_rows']}, "
        f"over-redacted {b['over_words']} -> {c['over_words']}.",
    ]
    if res["idents"]["new_examples"]:
        lines += ["", "New SE test identifier flags: " + ", ".join(f"`{x}`" for x in res["idents"]["new_examples"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_compound_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_compound_confirm.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
