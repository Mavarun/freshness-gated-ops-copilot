"""Train and evaluate the passage-level answer-support classifier.

    python scripts/build_passage_support.py --raw-dir /tmp/se_qa_raw

Needs the raw Stack Exchange pages of the QA snapshot (checked by SHA-256)
and the committed domain vectors. Writes ``data/domainvec/passage_support.json``
(feature scaling + logistic coefficients) and
``artifacts/passage_support_eval.{json,md}`` (out-of-sample, test questions).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.domain_vectors import default_vectors  # noqa: E402
from ops_copilot.passage_support import (  # noqa: E402
    DEFAULT_MODEL,
    FEATURES,
    LEXICAL_FEATURES,
    build_training_pairs,
    evaluate,
    fit_classifier,
    idf_from,
    pair_features,
)
from ops_copilot.qa_translation import is_test, pairs_from_page  # noqa: E402
from ops_copilot.qa_translation import load_table as load_qa_table  # noqa: E402

ART = ROOT / "artifacts"


def render_md(ev: dict, meta: dict, coef: dict) -> str:
    names = {"lexical coverage only": "lexical coverage only", "classifier, no vectors": "classifier, lexical features",
             "classifier": "classifier (+ domain vectors)"}
    lines = [
        "# Passage-level answer support: out-of-sample check (Stack Exchange test questions)",
        "",
        f"Trained on {meta['n_train_questions']:,} train-split questions ({meta['n_train_rows']:,} rows: own answer, "
        f"a hard negative sharing words, a random answer); evaluated on {ev['n_test_questions']:,} hash-held-out "
        "test questions the vectors and the classifier never saw.",
        "",
        "| scorer | AUC own vs hard negative | AUC own vs random | P@1 of 50 | MRR | P@1, own answer shares no title word (n) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for k, label in names.items():
        a, r, m = ev["auc"][k], ev["rank"][k], ev["rank_no_shared_word"][k]
        lines.append(
            f"| {label} | {a['vs_hard']:.3f} | {a['vs_random']:.3f} | {r['p_at_1']:.3f} | {r['mrr']:.3f} | "
            f"{m['p_at_1']:.3f} ({m['n']}) |"
        )
    lines += [
        "",
        "Chance P@1 is 0.020. Coefficients (standardised features): "
        + ", ".join(f"`{n}` {c:+.2f}" for n, c in zip(coef["features"], coef["coef"]))
        + f", intercept {coef['intercept']:+.2f}.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    args = ap.parse_args()
    files = sorted(args.raw_dir.glob("*.json.gz"))
    qa_meta = load_qa_table()["meta"]
    digest = hashlib.sha256()
    pairs: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for f in files:
        raw = gzip.decompress(f.read_bytes())
        digest.update(f.name.encode() + b"\0" + hashlib.sha256(raw).digest())
        site = f.name.split("-")[0]
        for p in pairs_from_page(site, json.loads(raw)):
            if (site, p["aid"]) not in seen:
                seen.add((site, p["aid"]))
                pairs.append(p)
    if digest.hexdigest() != qa_meta["raw_sha256"]:
        raise SystemExit("raw pages differ from the snapshot the QA table was built from")
    train = [p for p in pairs if not is_test(p["site"], p["qid"])]
    test = [p for p in pairs if is_test(p["site"], p["qid"])]
    idf = idf_from(p["a"] for p in train)
    dv = default_vectors()
    weight = lambda w: idf.get(w, 1.0)  # noqa: E731
    rows = build_training_pairs(train, idf)
    feats = [pair_features(q, a, weight, dv) for q, a, _, _ in rows]
    labels = [y for _, _, y, _ in rows]
    full = fit_classifier(feats, labels, FEATURES)
    lexical = fit_classifier(feats, labels, LEXICAL_FEATURES)
    ev = evaluate(test, {"lexical coverage only": None, "classifier, no vectors": lexical, "classifier": full}, idf, dv)
    meta = {
        "source": qa_meta["source"],
        "source_url": qa_meta["source_url"],
        "attribution": qa_meta["attribution"],
        "license": "CC BY-SA 4.0 (fitted from Stack Exchange posts, CC BY-SA 2.5 / 3.0 / 4.0)",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "raw_sha256": digest.hexdigest(),
        "n_train_questions": sum(1 for _, _, _, k in rows if k == "own"),
        "n_train_rows": len(rows),
        "vectors": "data/domainvec/se_ppmi_svd.json.gz",
    }
    DEFAULT_MODEL.write_text(json.dumps({"meta": meta, "classifier": full.as_dict()}, indent=1, sort_keys=True) + "\n")
    ART.mkdir(exist_ok=True)
    (ART / "passage_support_eval.json").write_text(
        json.dumps({"meta": meta, "eval": ev, "lexical_classifier": lexical.as_dict()}, indent=1, sort_keys=True) + "\n"
    )
    (ART / "passage_support_eval.md").write_text(render_md(ev, meta, full.as_dict()))
    for k in ev["auc"]:
        print(f"{k:28s} AUC hard {ev['auc'][k]['vs_hard']:.3f} random {ev['auc'][k]['vs_random']:.3f} "
              f"P@1 {ev['rank'][k]['p_at_1']:.3f} no-shared P@1 {ev['rank_no_shared_word'][k]['p_at_1']:.3f}")


if __name__ == "__main__":
    main()
