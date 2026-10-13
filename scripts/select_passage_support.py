"""Pick the passage classifier's training recipe on validation questions only.

    python scripts/select_passage_support.py --raw-dir /tmp/se_qa_raw

PR #19's hard negatives were picked by maximum lexical coverage, which favours
long answers (see ``passage_support.build_training_pairs``), and its overall
P@1 of 50 on test questions fell 0.679 -> 0.573. This script compares sampling
recipes on the *validation* questions of the train split (``qa_translation.
is_valid``, its own salt); test questions are not loaded at all.

Every candidate is fitted on train-minus-validation questions (IDF from the
same rows) and scored on validation questions. Rule, fixed in code before the
test split is read by ``build_passage_support.py``:

1. keep candidates whose validation AUC vs *length-matched* hard negatives is
   within ``AUC_TOL`` of the PR #19 recipe's (no loss of real hard-negative
   discrimination once length is taken away);
2. among those, take the highest validation MRR (rank of the own answer among
   50); ties go to fewer random negatives, then the narrower band.

Writes ``artifacts/passage_support_selection.{json,md}``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.domain_vectors import default_vectors  # noqa: E402
from ops_copilot.passage_support import (  # noqa: E402
    FEATURES,
    build_training_pairs,
    evaluate,
    fit_classifier,
    idf_from,
    length_profile,
    pair_features,
)
from ops_copilot.qa_translation import is_test, is_valid, pairs_from_page  # noqa: E402

ART = ROOT / "artifacts"
AUC_TOL = 0.005
BASELINE = ("max_lex", 1, 1.5)
GRID = [BASELINE, ("max_lex", 2, 1.5), ("max_lex", 3, 1.5)] + [
    ("length_matched", r, b) for r in (1, 2, 3) for b in (1.25, 1.5, 2.0)
]


def key(c: tuple[str, int, float]) -> str:
    return f"{c[0]}/r{c[1]}/b{c[2]}"


def select(rows: dict[str, dict], baseline: str = key(BASELINE), tol: float = AUC_TOL) -> str:
    floor = rows[baseline]["vs_hard_len"] - tol
    ok = [k for k, r in rows.items() if r["vs_hard_len"] >= floor]
    return max(ok, key=lambda k: (round(rows[k]["mrr"], 6), -rows[k]["n_random"], -rows[k]["band"]))


def load_pairs(raw_dir: Path) -> list[dict]:
    pairs: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for f in sorted(raw_dir.glob("*.json.gz")):
        site = f.name.split("-")[0]
        for p in pairs_from_page(site, json.loads(gzip.decompress(f.read_bytes()))):
            if (site, p["aid"]) not in seen:
                seen.add((site, p["aid"]))
                pairs.append(p)
    return pairs


def render_md(out: dict) -> str:
    lines = [
        "# Passage classifier: training-recipe selection (validation questions only)",
        "",
        f"Fitted on {out['n_fit_questions']:,} train-minus-validation questions, scored on "
        f"{out['n_valid_questions']:,} validation questions. Test questions were not loaded.",
        "",
        "Hard-negative length on the fit split (distinct words, median): "
        + ", ".join(f"{m}: own {p['own']['median']:.0f} / hard {p['hard']['median']:.0f}" for m, p in out["length"].items())
        + ".",
        "",
        f"Rule: AUC vs length-matched hard >= baseline - {out['auc_tol']}, then max MRR.",
        "",
        "| recipe | AUC vs hard | AUC vs length-matched hard | P@1 of 50 | MRR | no-shared-word P@1 (n) | kept |",
        "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for k, r in out["candidates"].items():
        mark = "**chosen**" if k == out["chosen"] else ("yes" if r["kept"] else "no")
        lines.append(
            f"| `{k}` | {r['vs_hard']:.3f} | {r['vs_hard_len']:.3f} | {r['p_at_1']:.3f} | {r['mrr']:.3f} | "
            f"{r['nos_p_at_1']:.3f} ({r['nos_n']}) | {mark} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    args = ap.parse_args()
    train = [p for p in load_pairs(args.raw_dir) if not is_test(p["site"], p["qid"])]
    fit = [p for p in train if not is_valid(p["site"], p["qid"])]
    valid = [p for p in train if is_valid(p["site"], p["qid"])]
    idf = idf_from(p["a"] for p in fit)
    dv = default_vectors()
    weight = lambda w: idf.get(w, 1.0)  # noqa: E731
    models, length = {}, {}
    for c in GRID:
        rows = build_training_pairs(fit, idf, mining=c[0], n_random=c[1], band=c[2])
        if c[1] == 1 and c[2] == 1.5:
            length[c[0]] = length_profile(rows)
        feats = [pair_features(q, a, weight, dv) for q, a, _, _ in rows]
        models[key(c)] = fit_classifier(feats, [y for _, _, y, _ in rows], FEATURES)
        print("fitted", key(c), flush=True)
    ev = evaluate(valid, models, idf, dv)
    cands = {}
    for c in GRID:
        k = key(c)
        a, r, n = ev["auc"][k], ev["rank"][k], ev["rank_no_shared_word"][k]
        cands[k] = {
            "mining": c[0], "n_random": c[1], "band": c[2],
            "vs_hard": a["vs_hard"], "vs_hard_len": a["vs_hard_len"], "vs_random": a["vs_random"],
            "p_at_1": r["p_at_1"], "mrr": r["mrr"], "nos_p_at_1": n["p_at_1"], "nos_n": n["n"],
        }
    chosen = select(cands)
    floor = cands[key(BASELINE)]["vs_hard_len"] - AUC_TOL
    for r in cands.values():
        r["kept"] = r["vs_hard_len"] >= floor
    out = {
        "n_fit_questions": sum(1 for _ in {(p["site"], p["qid"]) for p in fit}),
        "n_valid_questions": ev["n_test_questions"],
        "auc_tol": AUC_TOL,
        "baseline": key(BASELINE),
        "chosen": chosen,
        "length": length,
        "candidates": cands,
    }
    ART.mkdir(exist_ok=True)
    (ART / "passage_support_selection.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "passage_support_selection.md").write_text(render_md(out))
    for k, r in cands.items():
        print(f"{k:26s} hardLM {r['vs_hard_len']:.3f} P@1 {r['p_at_1']:.3f} MRR {r['mrr']:.3f} nosP@1 {r['nos_p_at_1']:.3f}")
    print("chosen:", chosen)


if __name__ == "__main__":
    main()
