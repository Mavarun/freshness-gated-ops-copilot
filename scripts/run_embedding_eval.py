#!/usr/bin/env python3
"""Latency and live-model parity for the optional embedding path.

Writes artifacts/embedding_eval.{md,json}:

- per-query latency p50 / p95 (perturbed rows, this machine) for the default
  config, each embedding ablation (frozen fixture), and, when
  sentence-transformers and the cached model are available, the live model;
- dense retriever agreement: how often BM25, the title-hash stub and the
  MiniLM dense retriever share a top-1 doc on the 254 eval queries;
- live vs frozen parity (only with the model): worst cosine between live query
  vectors and the committed fixture, and whether every decision matches.

Latency is wall-clock and machine-dependent, so it lives here and not in
robustness_metrics.json (which CI compares byte-for-byte).
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.embeddings import FrozenEmbeddings, model_available  # noqa: E402
from ops_copilot.eval import load_golden  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.robustness import EMBED_ABLATIONS, run_robustness  # noqa: E402


def _queries() -> list[str]:
    return [str(g["query"]) for g in load_golden()] + [
        str(r["query"]) for r in load_paraphrase_set()
    ]


def dense_agreement() -> dict:
    bot = Copilot(config=CopilotConfig(embedding_backend="frozen"))
    r = bot.retriever
    n = stub_bm25 = emb_bm25 = stub_emb = 0
    for q in _queries():
        rq = r.rewrite_query(q)
        b = [h.doc_id for h in r.search_bm25(rq, top_k=1)][:1]
        s = [h.doc_id for h in r.search_dense_stub(rq, top_k=1)][:1]
        e = [h.doc_id for h in r.search_dense(rq, top_k=1)][:1]
        n += 1
        stub_bm25 += b == s
        emb_bm25 += b == e
        stub_emb += s == e
    return {
        "n_queries": n,
        "bm25_vs_title_hash_stub_top1_agree": stub_bm25,
        "bm25_vs_minilm_top1_agree": emb_bm25,
        "title_hash_stub_vs_minilm_top1_agree": stub_emb,
    }


def parity() -> dict:
    frozen = Copilot(config=CopilotConfig(embedding_backend="frozen"))
    live = Copilot(config=CopilotConfig(embedding_backend="model"))
    fz = FrozenEmbeddings()
    worst = 1.0
    mismatched: list[str] = []
    for q in _queries():
        rq = frozen.retriever.rewrite_query(q)
        a, b = fz.vector(rq), live.embeddings.vector(rq)
        if a is not None and b is not None:
            worst = min(worst, float(np.dot(a, b)))
        if frozen.ask(q).decision != live.ask(q).decision:
            mismatched.append(q)
    return {"min_query_cosine_live_vs_fixture": worst, "decision_mismatches": mismatched}


def main() -> int:
    configs: dict[str, CopilotConfig] = {"default (embedding off)": CopilotConfig()}
    for label, knobs in EMBED_ABLATIONS.items():
        configs[f"{label} [frozen]"] = replace(CopilotConfig(), **knobs)
    have_model = model_available()
    if have_model:
        configs["both (embedding on) [live model]"] = CopilotConfig(embedding_backend="model")
    rows: dict[str, dict] = {}
    for label, cfg in configs.items():
        run_robustness(config=cfg)  # warm-up: model load, caches, imports
        rep = run_robustness(config=cfg)
        rows[label] = rep.latency_summary() | {
            "perturbed_accuracy": rep.perturbed_accuracy,
            "synonym_heldout": rep.per_synonym_split["heldout"]["perturbed_accuracy"],
            "n_fail_open": len(rep.fail_open),
        }
    out = {
        "machine": f"{platform.system()} {platform.machine()} python {platform.python_version()}",
        "model_available": have_model,
        "latency_ms": rows,
        "dense_agreement": dense_agreement(),
        "live_vs_frozen": parity() if have_model else None,
    }
    art = ROOT / "artifacts"
    (art / "embedding_eval.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# Embedding path: latency, dense agreement, live vs frozen",
        "",
        f"Machine: {out['machine']}. Latency is per perturbed row (n=203), after one "
        "warm-up pass, wall clock inside `Copilot.ask`.",
        "",
        "| config | p50 ms | p95 ms | mean ms | perturbed acc | held-out acc | fail-open |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, r in rows.items():
        lines.append(
            f"| {label} | {r['p50']:.2f} | {r['p95']:.2f} | {r['mean']:.2f} | "
            f"{r['perturbed_accuracy']:.3f} | {r['synonym_heldout']:.3f} | {r['n_fail_open']} |"
        )
    da = out["dense_agreement"]
    lines += [
        "",
        f"Dense top-1 agreement on {da['n_queries']} rewritten eval queries: BM25 vs "
        f"title-hash stub {da['bm25_vs_title_hash_stub_top1_agree']}, BM25 vs MiniLM "
        f"{da['bm25_vs_minilm_top1_agree']}, stub vs MiniLM "
        f"{da['title_hash_stub_vs_minilm_top1_agree']}.",
        "",
    ]
    if out["live_vs_frozen"]:
        lv = out["live_vs_frozen"]
        lines.append(
            f"Live model vs frozen fixture: worst query cosine "
            f"{lv['min_query_cosine_live_vs_fixture']:.6f}; decision mismatches "
            f"{len(lv['decision_mismatches'])} of {da['n_queries']}."
        )
    else:
        lines.append("Live model not installed here: live-vs-frozen parity skipped.")
    (art / "embedding_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
