"""One-shot check of ``attached_digit`` (pre-registered in ``passphrase_digit_protocol``).

    python scripts/run_passphrase_digit_check.py --raw-dir /tmp/se_qa_raw

Writes ``artifacts/passphrase_digit_check.{json,md}``. Seeds 3079 and 3083 are
spent once this has run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_compound_protocol as C  # noqa: E402
from ops_copilot import passphrase_digit_protocol as D  # noqa: E402
from ops_copilot import passphrase_tail_protocol as T  # noqa: E402
from ops_copilot.passphrase_identifiers import identifier_flags  # noqa: E402
from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows, wordlist_passphrases  # noqa: E402

ART = ROOT / "artifacts"


def run(raw_dir: Path | None) -> dict:
    ship, cand = D.shipped_detector(), D.candidate_detector()
    ps, pc = D.patterns_with(ship), D.patterns_with(cand)
    att = wordlist_passphrases(D.ATTACHED_SEED, D.N_ROWS, number_style="attached")
    std = wordlist_passphrases(D.STANDARD_SEED, D.N_ROWS)
    sa, ca, ss, cs = score_rows(att, ps), score_rows(att, pc), score_rows(std, ps), score_rows(std, pc)
    base_q = C.shipped_repo_queries()
    out: dict = {
        "attached": {"seed": D.ATTACHED_SEED, "shipped": sa["total"], "candidate": ca["total"],
                     "by_separator": {"shipped": sa["by_separator"], "candidate": ca["by_separator"]},
                     "candidate_cause": ca["cause"], "candidate_examples": ca["examples"]},
        "standard": {"seed": D.STANDARD_SEED, "shipped": ss["total"], "candidate": cs["total"]},
        "oct13_leak_words": sum(sum(_present(redact_query(t, pc).lower(), w) for w in ws) for t, ws in T.oct13_probe_texts()),
        "repo_query_changes": sum(redact_query(q, pc) != redact_query(q, ps) for q in base_q),
        "data_ident_new_flags": [f"{c} {n}" for n in T.data_identifiers() for c in T.IDENTIFIER_CUES
                                 if cand.search(f"{c} {n}") and not ship.search(f"{c} {n}")],
    }
    if raw_dir is not None:
        mat = D.se_material(raw_dir)
        out["se"] = {}
        for sp, m in mat.items():
            base_ids = set(identifier_flags(ship, m["identifiers"]))
            new = [n for n in identifier_flags(cand, m["identifiers"]) if n not in base_ids]
            out["se"][sp] = {
                "n_sentences": len(m["sentences"]),
                "sent_shipped": T.se_flags(ship, m["sentences"])["flagged"],
                "sent_candidate": T.se_flags(cand, m["sentences"])["flagged"],
                "n_identifiers": len(m["identifiers"]),
                "ident_shipped": len(base_ids),
                "ident_new": len(new),
                "ident_new_examples": new[:12],
            }
    out["checks"] = D.checks(out)
    out["ships"] = raw_dir is not None and all(out["checks"].values())
    return out


def render(out: dict) -> str:
    a, s = out["attached"], out["standard"]
    lines = [
        "# attached_digit: one-shot check (pre-registered in `ops_copilot.passphrase_digit_protocol`)",
        "",
        "| rows | leak rows (shipped -> knob) | leak words (shipped -> knob) | over-redacted |",
        "| --- | ---: | ---: | ---: |",
        f"| Bitwarden shape, seed {a['seed']} | {a['shipped']['leak_rows']} -> {a['candidate']['leak_rows']} of {a['shipped']['rows']:,} | "
        f"{a['shipped']['leak_words']} -> {a['candidate']['leak_words']} of {a['shipped']['words']:,} | {a['shipped']['over_words']} -> {a['candidate']['over_words']} |",
        f"| Oct 29 shape, seed {s['seed']} | {s['shipped']['leak_rows']} -> {s['candidate']['leak_rows']} | "
        f"{s['shipped']['leak_words']} -> {s['candidate']['leak_words']} of {s['shipped']['words']:,} | {s['shipped']['over_words']} -> {s['candidate']['over_words']} |",
        "",
        f"Oct 13 probe leaks {out['oct13_leak_words']}; trace queries changed {out['repo_query_changes']}; "
        f"data/ ids newly flagged {len(out['data_ident_new_flags'])}.",
    ]
    for sp, e in out.get("se", {}).items():
        lines.append(
            f"SE {sp}: sentences flagged {e['sent_shipped']} -> {e['sent_candidate']} of {e['n_sentences']:,}; identifiers "
            f"newly flagged {e['ident_new']} of {e['n_identifiers']:,} (shipped already flags {e['ident_shipped']})"
            + (f": {', '.join(f'`{x}`' for x in e['ident_new_examples'])}" if e["ident_new_examples"] else "") + "."
        )
    lines += ["", "Checks: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in out["checks"].items()), "",
              f"**{'Ships on.' if out['ships'] else 'Ships off.'}** Seeds {a['seed']} and {s['seed']} are spent.", "",
              "Leak causes with the knob (Bitwarden rows): " + ", ".join(f"{k} {v}" for k, v in out["attached"]["candidate_cause"].items())]
    lines += ["", "Still leaking (first few):", ""] + [f"- `{e['text']}`" for e in a["candidate_examples"][:6]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = run(ap.parse_args().raw_dir)
    (ART / "passphrase_digit_check.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passphrase_digit_check.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
