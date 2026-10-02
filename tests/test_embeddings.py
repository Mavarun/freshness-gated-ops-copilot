"""Optional embedding backend: frozen fixture integrity, offline default, live parity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot import embeddings as emb
from ops_copilot.embeddings import (
    CORPUS_FIXTURE,
    MANIFEST,
    QUERY_FIXTURE,
    EmbeddingUnavailable,
    FrozenEmbeddings,
    evidence_sentences,
    evidence_text,
    model_available,
    passage_text,
    resolve_backend,
    text_key,
)
from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import load_paraphrase_set

ROOT = Path(__file__).resolve().parents[1]
FROZEN = replace(CopilotConfig(), embedding_backend="frozen")
needs_model = pytest.mark.skipif(
    not model_available(), reason="sentence-transformers or the cached MiniLM model is not installed"
)


@pytest.fixture(scope="module")
def frozen() -> FrozenEmbeddings:
    return FrozenEmbeddings()


def _eval_queries() -> list[str]:
    return [str(g["query"]) for g in load_golden()] + [
        str(r["query"]) for r in load_paraphrase_set()
    ]


def test_default_config_keeps_the_offline_backend(copilot: Copilot) -> None:
    cfg = CopilotConfig()
    assert cfg.embedding_backend == "off"
    assert copilot.embeddings is None
    assert copilot.retriever.dense_embed is None
    assert copilot.grounder.embed_support is None
    res = copilot.ask("What is the current checkout p99 latency?")
    assert res.disagreement["dense_name"] == "title_hash_dense_stub"


def test_fixture_files_are_small_float16_and_match_the_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["model"] == emb.DEFAULT_MODEL
    assert manifest["dtype"] == "float16"
    for path in (CORPUS_FIXTURE, QUERY_FIXTURE):
        assert path.stat().st_size < 400_000, path.name
        meta = manifest["files"][path.name]
        assert meta["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path, allow_pickle=False) as data:
            assert data["vectors"].dtype == np.float16
            assert data["vectors"].shape == (meta["n"], meta["dim"]) == (meta["n"], 384)
            keys = [str(k) for k in data["keys"]]
            assert keys == [text_key(str(t)) for t in data["texts"]]
            assert len(set(keys)) == len(keys)
            norms = np.linalg.norm(data["vectors"].astype(np.float64), axis=1)
            assert np.allclose(norms, 1.0, atol=2e-3)


def test_fixture_covers_every_passage_sentence_and_eval_query(frozen, copilot) -> None:
    corpus = []
    for chunk in copilot.corpus.chunks:
        corpus.append(passage_text(chunk))
        corpus.extend(evidence_sentences(evidence_text(chunk)))
    assert all(v is not None for v in frozen.lookup(corpus))
    rewritten = [copilot.retriever.rewrite_query(q) for q in _eval_queries()]
    assert all(v is not None for v in frozen.lookup(rewritten))


def test_frozen_miss_is_none_and_counted(frozen) -> None:
    before = frozen.stats["miss"]
    assert frozen.vector("a query that was never frozen into the fixture") is None
    assert frozen.stats["miss"] == before + 1


def test_resolve_backend_modes(monkeypatch) -> None:
    assert resolve_backend("off") is None
    assert isinstance(resolve_backend("frozen"), FrozenEmbeddings)
    with pytest.raises(ValueError):
        resolve_backend("openai")
    monkeypatch.setattr(emb, "model_available", lambda *_a, **_k: False)
    assert isinstance(resolve_backend("auto"), FrozenEmbeddings)
    with pytest.raises(EmbeddingUnavailable):
        resolve_backend("frozen", fixture_paths=[ROOT / "data" / "embeddings" / "nope.npz"])


def test_model_backend_without_the_package_raises_cleanly(monkeypatch) -> None:
    real = emb.importlib.util.find_spec
    monkeypatch.setattr(
        emb.importlib.util,
        "find_spec",
        lambda name, *a: None if name == "sentence_transformers" else real(name, *a),
    )
    assert model_available() is False
    with pytest.raises(EmbeddingUnavailable):
        emb.ModelEmbeddings()


def test_frozen_path_never_imports_torch_or_downloads() -> None:
    code = (
        "import sys\n"
        "from dataclasses import replace\n"
        "from ops_copilot import Copilot, CopilotConfig\n"
        "bot = Copilot(config=replace(CopilotConfig(), embedding_backend='frozen'))\n"
        "r = bot.ask('What is the health of the payments-api?')\n"
        "assert r.disagreement['dense_name'] == 'minilm_dense', r.disagreement\n"
        "bad = [m for m in ('torch', 'sentence_transformers', 'transformers') if m in sys.modules]\n"
        "assert not bad, bad\n"
        "print('ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src"), "HF_HUB_OFFLINE": "1", "PATH": ""},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


def test_frozen_runs_are_deterministic() -> None:
    a = Copilot(config=FROZEN)
    b = Copilot(config=FROZEN)
    for q in ("What is the health of the payments-api?", "What is the checkout canary stickiness salt?"):
        ra, rb = a.ask(q), b.ask(q)
        assert ra.decision == rb.decision
        assert ra.disagreement == rb.disagreement
        assert ra.grounding.as_dict() == rb.grounding.as_dict()


@needs_model
def test_live_model_matches_the_frozen_fixture(frozen, copilot) -> None:
    live = emb.ModelEmbeddings()
    queries = [copilot.retriever.rewrite_query(q) for q in _eval_queries()[::7]]
    chunks = copilot.corpus.chunks[::9]
    texts = queries + [passage_text(c) for c in chunks]
    fresh = live.encode_raw(texts).astype(np.float64)
    for text, vec in zip(texts, fresh):
        ref = frozen.vector(text)
        assert ref is not None
        assert float(np.dot(ref, vec / np.linalg.norm(vec))) > 0.999, text


@needs_model
def test_live_model_decisions_match_frozen_on_the_golden_set() -> None:
    frozen_bot = Copilot(config=FROZEN)
    live_bot = Copilot(config=replace(CopilotConfig(), embedding_backend="model"))
    assert live_bot.embeddings.name == "model"
    for case in load_golden():
        q = str(case["query"])
        assert frozen_bot.ask(q).decision == live_bot.ask(q).decision, q


@needs_model
def test_live_model_handles_queries_outside_the_fixture() -> None:
    live_bot = Copilot(config=replace(CopilotConfig(), embedding_backend="model"))
    res = live_bot.ask("Which on-duty person owns checkout right now, roughly?")
    assert res.disagreement["dense_name"] == "minilm_dense"
    assert live_bot.embeddings.stats["encoded"] >= 1


@needs_model
def test_precompute_check_reports_no_missing_texts() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "precompute_embeddings.py"), "--check"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "minilm_corpus.npz" in proc.stdout and "missing=0" in proc.stdout
    for line in proc.stdout.splitlines():
        if "min_cos=" in line:
            assert float(line.rsplit("min_cos=", 1)[1]) > 0.999
