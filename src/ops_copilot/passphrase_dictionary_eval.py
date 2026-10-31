"""Scoring for the Oct 31 protocol (``passphrase_dictionary_protocol``); rules live there."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_arm(arm, probes: dict[str, list], se: dict[str, list[str]], *, base_queries: dict[str, str],
                 base_ident_flags: set[str]) -> dict[str, Any]:
    from ops_copilot import passphrase_compound_protocol as C
    from ops_copilot import passphrase_dictionary_protocol as P
    from ops_copilot import passphrase_tail_protocol as T
    from ops_copilot.passphrase_identifiers import identifier_flags
    from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows

    pats, det = P.patterns_for(arm), P.detector(arm)
    base = C.detector(("all4", True, True))
    flagged = identifier_flags(det, se["identifiers"])
    new = [n for n in flagged if n not in base_ident_flags]
    return {
        "arm": P.arm_name(arm),
        "probe": {k: score_rows(rows, pats) for k, rows in probes.items()},
        "oct13_leak_words": sum(sum(_present(redact_query(t, pats).lower(), w) for w in ws) for t, ws in T.oct13_probe_texts()),
        "repo_query_changes": sum(redact_query(q, pats) != red for q, red in base_queries.items()),
        "data_ident_new_flags": [f"{c} {n}" for n in T.data_identifiers() for c in T.IDENTIFIER_CUES
                                 if det.search(f"{c} {n}") and not base.search(f"{c} {n}")],
        "se": {
            "sent_flagged": T.se_flags(det, se["sentences"])["flagged"],
            "ident_flagged": len(flagged),
            "ident_new": len(new),
            "ident_new_examples": new[:12],
            "ident_unflagged_examples": sorted(base_ident_flags - set(flagged))[:12],
            "ident_unflagged": len(base_ident_flags - set(flagged)),
        },
    }


def run_phase(seeds: dict[str, int], split: str, raw_dir: Path, arms) -> dict[str, Any]:
    from ops_copilot import passphrase_compound_protocol as C
    from ops_copilot import passphrase_dictionary_protocol as P
    from ops_copilot import passphrase_digit_protocol as D
    from ops_copilot.passphrase_identifiers import identifier_flags

    probes = {k: P.probe_rows(k, s) for k, s in seeds.items()}
    se = D.se_material(raw_dir)[split]
    base_q = C.shipped_repo_queries()
    base_ids = set(identifier_flags(P.detector(P.SHIPPED), se["identifiers"]))
    results = [evaluate_arm(a, probes, se, base_queries=base_q, base_ident_flags=base_ids) for a in arms]
    return {"seeds": seeds, "split": split, "rows": P.N_ROWS, "se_sentences": len(se["sentences"]),
            "se_identifiers": len(se["identifiers"]), "results": results}


def table(results: list[dict], checks_key: str = "safe") -> list[str]:
    lines = [
        "| arm | leak words std / glued / invented (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | safe |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in results:
        p = r["probe"]
        lw = [p[k]["total"]["leak_words"] for k in ("standard", "attached", "invented")]
        ov = sum(p[k]["total"]["over_words"] for k in ("standard", "attached", "invented"))
        chk = r.get(checks_key, {})
        safe = "yes" if all(chk.values()) else "no: " + ", ".join(k for k, v in chk.items() if not v)
        lines.append(
            f"| {r['arm']} | {lw[0]} / {lw[1]} / {lw[2]} ({sum(lw)}) | {ov} | {r['se']['sent_flagged']} | "
            f"{r['se']['ident_flagged']} ({r['se']['ident_new']}) | {r['oct13_leak_words']} / {r['repo_query_changes']} / "
            f"{len(r['data_ident_new_flags'])} | {safe} |"
        )
    return lines
