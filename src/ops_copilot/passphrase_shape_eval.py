"""Scoring for the Nov 1 protocol (``passphrase_shape_protocol``); the rules live there."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_arm(arm, probes: dict[str, list], se: dict[str, list[str]], *, base_queries: dict[str, str],
                 base_ident_flags: set[str]) -> dict[str, Any]:
    from ops_copilot import passphrase_shape_protocol as S
    from ops_copilot import passphrase_tail_protocol as T
    from ops_copilot.passphrase import shape_guard_hits
    from ops_copilot.passphrase_identifiers import identifier_flags
    from ops_copilot.passphrase_wordlist import _present, redact_query, score_rows

    pats, det = S.patterns_for(arm), S.detector(arm)
    base = S.detector(S.SHIPPED)
    flagged = identifier_flags(det, se["identifiers"])
    new = [n for n in flagged if n not in base_ident_flags]
    removed = sorted(base_ident_flags - set(flagged))
    by_guard: dict[str, int] = {}
    for n in removed:
        sep = next(c for c in n if c in "-._")
        for g in shape_guard_hits(n.split(sep), sep, arm):
            by_guard[g] = by_guard.get(g, 0) + 1
    return {
        "arm": S.arm_name(arm),
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
            "ident_unflagged": len(removed),
            "ident_unflagged_by_guard": dict(sorted(by_guard.items())),
            "ident_unflagged_examples": removed[:12],
            "ident_still_flagged_examples": flagged[:12],
        },
    }


def run_phase(seeds: dict[str, int], split: str, raw_dir: Path, arms) -> dict[str, Any]:
    from ops_copilot import passphrase_digit_protocol as D
    from ops_copilot import passphrase_shape_protocol as S
    from ops_copilot import passphrase_tail_protocol as T
    from ops_copilot.passphrase_identifiers import identifier_flags
    from ops_copilot.passphrase_wordlist import redact_query

    probes = {k: S.probe_rows(k, s) for k, s in seeds.items()}
    se = D.se_material(raw_dir)[split]
    # Baseline queries come from the Oct 31 shipped detector (the protocol's SHIPPED arm).
    pats = S.patterns_for(S.SHIPPED)
    base_q = {q: redact_query(q, pats) for q in dict.fromkeys(T.repo_queries())}
    base_ids = set(identifier_flags(S.detector(S.SHIPPED), se["identifiers"]))
    results = [evaluate_arm(a, probes, se, base_queries=base_q, base_ident_flags=base_ids) for a in arms]
    return {"seeds": seeds, "split": split, "rows": S.N_ROWS, "se_sentences": len(se["sentences"]),
            "se_identifiers": len(se["identifiers"]), "results": results}


def table(results: list[dict], checks_key: str = "safe") -> list[str]:
    from ops_copilot.passphrase_shape_protocol import PROBES

    lines = [
        "| arm | leak words std / glued / invented / cased / phrase (total) | over words | SE sentences flagged "
        "| SE ids flagged (new) | Oct 13 / queries / data ids | checks |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in results:
        p = r["probe"]
        lw = [p[k]["total"]["leak_words"] for k in PROBES]
        ov = sum(p[k]["total"]["over_words"] for k in PROBES)
        chk = r.get(checks_key, {})
        ok = "yes" if all(chk.values()) else "no: " + ", ".join(k for k, v in chk.items() if not v)
        lines.append(
            f"| {r['arm']} | {' / '.join(map(str, lw))} ({sum(lw)}) | {ov} | {r['se']['sent_flagged']} | "
            f"{r['se']['ident_flagged']} ({r['se']['ident_new']}) | {r['oct13_leak_words']} / {r['repo_query_changes']} / "
            f"{len(r['data_ident_new_flags'])} | {ok} |"
        )
    return lines
