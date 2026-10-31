"""Post-hoc look at the Oct 31 dictionary rule that did not ship (spent rows only, after the confirm).

    python scripts/run_passphrase_dictionary_posthoc.py [--raw-dir /tmp/se_qa_raw]

On the spent calibration and confirm invented-word rows it splits the dictionary
rule's leaks by word shape (consonant-vowel vs closed-syllable) and separator, so it
says which invented passphrases the rule gives away. With ``--raw-dir`` it also
counts what the rule would stop flagging among the SE *train* identifiers, by shape
(all-caps, mixed case, lower case). Writes
``artifacts/passphrase_dictionary_posthoc.{json,md}``. Nothing here gates or ships.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_dictionary_protocol as P  # noqa: E402
from ops_copilot.passphrase_wordlist import invented_words, score_rows  # noqa: E402

ART = ROOT / "artifacts"
ARMS = (P.SHIPPED, (("dict", "compounds"), "guard"), (("dict_cv", "compounds"), "guard"))


def _shape(name: str) -> str:
    letters = [c for c in name if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return "all_caps"
    if any(c.isupper() for c in letters):
        return "mixed_case"
    return "lower"


def run(raw_dir: Path | None) -> dict:
    cv = set(invented_words("cv"))
    out: dict = {"invented": {}}
    for seed in (P.CALIB_INVENTED_SEED, P.CONFIRM_INVENTED_SEED):
        rows = P.probe_rows("invented", seed)
        groups = {"cv": [r for r in rows if set(r.words) <= cv], "cvc": [r for r in rows if not set(r.words) <= cv]}
        cell: dict = {}
        for arm in ARMS:
            pats = P.patterns_for(arm)
            cell[P.arm_name(arm)] = {
                g: {"rows": len(rs), **{k: v for k, v in score_rows(rs, pats).items() if k in ("total", "by_separator")}}
                for g, rs in groups.items()
            }
        out["invented"][str(seed)] = cell
    if raw_dir is not None:
        from ops_copilot import passphrase_digit_protocol as D
        from ops_copilot.passphrase_identifiers import identifier_flags

        ids = D.se_material(raw_dir)["train"]["identifiers"]
        ship = set(identifier_flags(P.detector(P.SHIPPED), ids))
        out["se_train"] = {"shipped_flags": len(ship)}
        for arm in ARMS[1:]:
            kept = set(identifier_flags(P.detector(arm), ids))
            dropped = sorted(ship - kept)
            by: dict = {}
            for n in dropped:
                by[_shape(n)] = by.get(_shape(n), 0) + 1
            out["se_train"][P.arm_name(arm)] = {"still_flagged": len(kept), "dropped": len(dropped), "dropped_by_shape": by,
                                                "still_flagged_examples": sorted(kept)[:15]}
    return out


def render(out: dict) -> str:
    lines = ["# Dictionary rule, post-hoc (spent rows; nothing ships from this)", "",
             "| seed | words | arm | cv rows: leak rows / words | cvc rows: leak rows / words |", "| --- | --- | --- | ---: | ---: |"]
    for seed, cell in out["invented"].items():
        for arm, g in cell.items():
            lines.append(f"| {seed} | invented | {arm} | {g['cv']['total']['leak_rows']} / {g['cv']['total']['leak_words']} of "
                         f"{g['cv']['total']['words']} | {g['cvc']['total']['leak_rows']} / {g['cvc']['total']['leak_words']} of {g['cvc']['total']['words']} |")
    for seed, cell in out["invented"].items():
        sep = cell["dict/compounds/guard"]["cvc"]["by_separator"]
        lines += ["", f"Seed {seed}, `dict/compounds/guard`, closed-syllable rows leaking by separator: "
                  + ", ".join(f"{k} {v['leak_rows']} of {v['rows']}" for k, v in sorted(sep.items()))]
    if "se_train" in out:
        s = out["se_train"]
        lines += ["", f"SE train identifiers flagged by the shipped detector: {s['shipped_flags']}."]
        for arm in ("dict/compounds/guard", "dict_cv/compounds/guard"):
            e = s[arm]
            lines.append(f"- `{arm}`: still flags {e['still_flagged']}; stops flagging {e['dropped']} ("
                         + ", ".join(f"{k} {v}" for k, v in sorted(e["dropped_by_shape"].items())) + "). Still flagged: "
                         + ", ".join(f"`{x}`" for x in e["still_flagged_examples"][:8]))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_dictionary_posthoc.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_dictionary_posthoc.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
