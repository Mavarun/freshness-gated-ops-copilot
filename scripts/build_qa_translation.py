#!/usr/bin/env python3
"""Train the QA translation model on the fetched pages and commit its table.

    python scripts/fetch_stackexchange_qa.py --raw-dir /tmp/se_qa_raw   # once
    python scripts/build_qa_translation.py --raw-dir /tmp/se_qa_raw

Steps (deterministic; no randomness except the seeded candidate draw in the
out-of-sample ranking eval):

1. every raw page -> (title words, answer words) pairs (``pairs_from_page``);
2. split by a salted hash of (site, question id): 90% train / 10% test;
3. pick the EM iteration count on a validation slice of train (independent
   hash; best MRR of ``ITERATION_GRID``), then IBM Model 1 EM on all *train*
   pairs with that count;
4. out-of-sample answer ranking on the test questions (BM25 vs the model),
   run once with the chosen count;
5. write the corpus-bound table ``data/qa/se_qa_translation.json.gz`` and the
   ranking report ``artifacts/qa_translation_eval.{json,md}``.

The raw pages are not committed (about 200 MB); ``meta.raw_sha256`` pins them.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.corpus import Corpus  # noqa: E402
from ops_copilot.qa_translation import (  # noqa: E402
    DEFAULT_TABLE,
    ITERATION_GRID,
    MAX_ANSWER_TOKENS,
    MAX_ANSWERS_PER_QUESTION,
    MAX_TITLE_TOKENS,
    MIN_A_DF,
    MIN_Q_DF,
    TEST_FRACTION,
    build_table,
    dump_table,
    is_test,
    is_valid,
    pairs_from_page,
    rank_eval,
    train_model1,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--report", type=Path, default=ROOT / "artifacts" / "qa_translation_eval")
    args = ap.parse_args()
    files = sorted(args.raw_dir.glob("*.json.gz"))
    if not files:
        raise SystemExit(f"no raw pages in {args.raw_dir}")
    digest = hashlib.sha256()
    pairs: list[dict] = []
    licences: Counter[str] = Counter()
    sites: Counter[str] = Counter()
    questions: set[tuple[str, int]] = set()
    seen_answers: set[tuple[str, int]] = set()
    for f in files:
        raw = gzip.decompress(f.read_bytes())
        digest.update(f.name.encode() + b"\0" + hashlib.sha256(raw).digest())
        site = f.name.split("-")[0]
        for p in pairs_from_page(site, json.loads(raw)):
            if (site, p["aid"]) in seen_answers:
                continue  # the same question can sit in both the votes and activity pages
            seen_answers.add((site, p["aid"]))
            pairs.append(p)
            licences[p["license"]] += 1
            sites[site] += 1
            questions.add((site, p["qid"]))
    train = [p for p in pairs if not is_test(p["site"], p["qid"])]
    test = [p for p in pairs if is_test(p["site"], p["qid"])]
    fit = [p for p in train if not is_valid(p["site"], p["qid"])]
    valid = [p for p in train if is_valid(p["site"], p["qid"])]
    selection = []
    for it in ITERATION_GRID:
        m = train_model1(fit, iterations=it)
        r = rank_eval(m, valid, fit, max_queries=500)
        selection.append({"iterations": it, "valid_mrr": r["translation"]["mrr"],
                          "valid_p_at_1": r["translation"]["p_at_1"]})
        print(f"validation: {it} EM iterations -> MRR {r['translation']['mrr']:.3f}", flush=True)
    best_it = max(selection, key=lambda x: (round(x["valid_mrr"], 6), -x["iterations"]))["iterations"]
    t0 = time.perf_counter()
    model = train_model1(train, iterations=best_it)
    train_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    ranking = rank_eval(model, test, train)
    eval_s = time.perf_counter() - t0
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    meta = {
        "source": "Stack Exchange API v2.3, /questions sort=votes (most-voted questions) with answers",
        "sites": dict(sorted(sites.items())),
        "attribution": "Questions and answers by the users of serverfault.com, superuser.com, "
        "unix.stackexchange.com, askubuntu.com, dba.stackexchange.com, security.stackexchange.com, "
        "devops.stackexchange.com and networkengineering.stackexchange.com; Stack Exchange Inc.",
        "licenses": dict(sorted(licences.items())),
        "fetched": "2026-10-08",
        "raw_pages": len(files),
        "raw_sha256": digest.hexdigest(),
        "n_questions": len(questions),
        "n_pairs": len(pairs),
        "n_train_pairs": len(train),
        "n_test_pairs": len(test),
        "test_fraction": TEST_FRACTION,
        "max_title_tokens": MAX_TITLE_TOKENS,
        "max_answer_tokens": MAX_ANSWER_TOKENS,
        "max_answers_per_question": MAX_ANSWERS_PER_QUESTION,
        "min_q_df": MIN_Q_DF,
        "min_a_df": MIN_A_DF,
        "em_iterations": best_it,
        "iteration_selection": selection,
        "n_valid_pairs": len(valid),
        "q_vocab": len(model.q_vocab),
        "a_vocab": len(model.a_vocab) - 1,
        "em_log": model.log,
    }
    table = build_table(model, texts, meta)
    sha = dump_table(table, args.out)
    report = {"meta": {k: v for k, v in meta.items() if k != "em_log"}, "em_log": model.log,
              "table_sha256": sha, "train_seconds": round(train_s, 1), "eval_seconds": round(eval_s, 1),
              "ranking": ranking, "table_entries": sum(len(v) for v in table["table"].values()),
              "table_evidence_words": len(table["table"])}
    args.report.with_suffix(".json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    r = ranking
    lines = [
        "# QA translation model: out-of-sample answer ranking (outside data)",
        "",
        f"Model: IBM Model 1, question <- answer, {best_it} EM iterations (picked by validation MRR "
        f"over {list(ITERATION_GRID)} on a hash slice of train), trained on "
        f"{len(train):,} (title, answer) pairs from {len(questions):,} most-voted questions of "
        f"{len(sites)} ops Stack Exchange sites (CC BY-SA). Test: {len(test):,} pairs of the "
        f"hash-held-out {TEST_FRACTION:.0%} of questions, never seen in training.",
        "",
        f"Task: rank each test question's own answer among {r['n_candidates']} candidates "
        f"(the others are answers to other test questions, seed {r['seed']}); "
        f"{r['n_queries']} test questions. {r['share_no_title_overlap']:.1%} of true answers share "
        "no content word with their title.",
        "",
        "| scorer | P@1 | MRR | P@1 when the answer shares no title word |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in ("bm25", "translation", "combined"):
        x = r[name]
        no = "-" if x["p_at_1_no_overlap"] is None else f"{x['p_at_1_no_overlap']:.3f}"
        lines.append(f"| {name} | {x['p_at_1']:.3f} | {x['mrr']:.3f} | {no} |")
    lines += [
        "",
        f"Chance P@1 is {1 / r['n_candidates']:.3f}. Training took {train_s:.0f} s, the ranking eval "
        f"{eval_s:.0f} s (box CPU). Table: {report['table_evidence_words']} corpus words x top "
        f"question words ({report['table_entries']:,} entries), SHA-256 `{sha}`.",
        "",
    ]
    args.report.with_suffix(".md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
