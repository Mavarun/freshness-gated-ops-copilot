#!/usr/bin/env python3
"""Freeze sentence embeddings for the corpus and the eval queries.

Run locally with the optional extra installed (``pip install -e ".[embed]"``);
CI never runs this and never downloads a model. Writes, under
``data/embeddings/``:

- ``minilm_corpus.npz``: one vector per chunk passage (dense retriever) and
  per evidence sentence (semantic grounding);
- ``minilm_queries.npz``: one vector per *rewritten* query
  (``Retriever.rewrite_query`` under the default config) for the 51 clean
  golden queries and the 203 perturbed rows;
- ``minilm_write.npz``: the write-prototype backoff's spans: lexicon
  prototypes, the dev calibration verbs (``data/write/prototype_dev.jsonl``)
  and the masked ``"<verb> the <kind>"`` span of every golden / perturbed /
  write-intent-eval query that reaches the backoff;
- ``manifest.json``: model, dtype, counts, fingerprints, and file hashes.

``--only write`` rebuilds just the write fixture (the others stay byte-identical).

Vectors are L2-normalised, encoded one text at a time, and stored as float16.
The npz files hold ``keys`` (sha1 of the exact text), ``texts``, ``vectors``,
and ``meta``. ``--check`` re-encodes everything and reports the worst cosine
against the committed files without writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.embeddings import (  # noqa: E402
    CORPUS_FIXTURE,
    DEFAULT_MODEL,
    MANIFEST,
    QUERY_FIXTURE,
    WRITE_FIXTURE,
    ModelEmbeddings,
    evidence_sentences,
    evidence_text,
    passage_text,
    text_key,
)
from ops_copilot.eval import load_golden  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402


def corpus_texts(bot: Copilot) -> list[str]:
    texts: list[str] = []
    for chunk in bot.corpus.chunks:
        texts.append(passage_text(chunk))
        texts.extend(evidence_sentences(evidence_text(chunk)))
    return list(dict.fromkeys(t.strip() for t in texts if t.strip()))


def query_texts(bot: Copilot) -> list[str]:
    queries = [str(g["query"]) for g in load_golden()]
    queries += [str(r["query"]) for r in load_paraphrase_set()]
    rewritten = [bot.retriever.rewrite_query(q) for q in queries]
    return list(dict.fromkeys(t.strip() for t in rewritten if t.strip()))


def write_texts() -> list[str]:
    from ops_copilot.write_intent import classify_write_intent
    from ops_copilot.write_prototypes import all_prototype_spans, load_dev_set, span

    class Recorder:
        def __init__(self) -> None:
            self.spans: list[str] = []

        def match(self, verb: str, target_kind: str):
            self.spans.append(span(verb, target_kind))
            return None

    rec = Recorder()
    queries = [str(g["query"]) for g in load_golden()]
    queries += [str(r["query"]) for r in load_paraphrase_set()]
    eval_set = ROOT / "data" / "golden" / "write_intent_eval.jsonl"
    if eval_set.is_file():
        queries += [json.loads(ln)["query"] for ln in eval_set.read_text("utf-8").splitlines() if ln.strip()]
    for q in queries:
        classify_write_intent(q, prototypes=rec)
    texts = all_prototype_spans() + [span(r["verb"], r["kind"]) for r in load_dev_set()] + rec.spans
    return list(dict.fromkeys(texts))


def fingerprint(texts: list[str]) -> str:
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16]


def _save(path: Path, texts: list[str], vecs: np.ndarray, meta: dict) -> None:
    np.savez_compressed(
        path,
        keys=np.array([text_key(t) for t in texts]),
        texts=np.array(texts),
        vectors=vecs.astype(np.float16),
        meta=np.array(json.dumps(meta, sort_keys=True)),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--allow-download", action="store_true")
    ap.add_argument("--check", action="store_true", help="compare with committed files only")
    ap.add_argument("--only", choices=("corpus", "queries", "write"), default=None)
    args = ap.parse_args(argv)

    bot = Copilot(config=CopilotConfig())
    sets = {
        CORPUS_FIXTURE: ("corpus", lambda: corpus_texts(bot)),
        QUERY_FIXTURE: ("queries", lambda: query_texts(bot)),
        WRITE_FIXTURE: ("write", write_texts),
    }
    if args.only:
        sets = {p: v for p, v in sets.items() if v[0] == args.only}
    sets = {p: (kind, make()) for p, (kind, make) in sets.items()}
    backend = ModelEmbeddings(args.model, allow_download=args.allow_download, document_cache=None)
    manifest: dict = {"model": args.model, "dtype": "float16", "normalized": True, "files": {}}
    if args.only and MANIFEST.is_file():
        manifest["files"] = json.loads(MANIFEST.read_text(encoding="utf-8")).get("files", {})
    for path, (kind, texts) in sets.items():
        vecs = backend.encode_raw(texts)
        if args.check:
            with np.load(path, allow_pickle=False) as old:
                ref = dict(zip((str(k) for k in old["keys"]), old["vectors"].astype(np.float64)))
            cos = [
                float(np.dot(ref[text_key(t)], v.astype(np.float64)))
                for t, v in zip(texts, vecs)
                if text_key(t) in ref
            ]
            n_missing = sum(1 for t in texts if text_key(t) not in ref)
            print(f"{path.name}: n={len(texts)} missing={n_missing} min_cos={min(cos):.6f}")
            continue
        meta = {
            "model": args.model,
            "kind": kind,
            "n": len(texts),
            "dim": int(vecs.shape[1]),
            "fingerprint": fingerprint(texts),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        _save(path, texts, vecs, meta)
        manifest["files"][path.name] = meta | {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        print(f"wrote {path.relative_to(ROOT)} n={len(texts)} bytes={path.stat().st_size}")
    if not args.check:
        try:
            import sentence_transformers
            import torch

            manifest["versions"] = {
                "sentence_transformers": sentence_transformers.__version__,
                "torch": torch.__version__,
                "numpy": np.__version__,
            }
        except ImportError:  # pragma: no cover
            pass
        MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
