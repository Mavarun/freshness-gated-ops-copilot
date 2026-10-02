"""Optional sentence-embedding backends (``pip install -e ".[embed]"``).

Two interchangeable backends return L2-normalised vectors for exact text
strings:

- ``FrozenEmbeddings`` reads the committed float16 fixtures in
  ``data/embeddings/`` (corpus passages, evidence sentences, the golden +
  perturbed queries, and the write-prototype spans, all produced by ``scripts/precompute_embeddings.py`` with
  ``sentence-transformers/all-MiniLM-L6-v2``). It needs only numpy, never
  downloads anything, and is what CI uses to evaluate the embedding path.
  A text that is not in the fixture is a *miss*: callers fall back to the
  offline behaviour (title-hash dense stub, lexical-only grounding).
- ``ModelEmbeddings`` runs the real model through sentence-transformers. It
  loads from the local Hugging Face cache only (``allow_download=False`` by
  default), reuses the committed corpus fixture as its document cache when the
  model name matches, encodes every other text one at a time (batch size 1,
  so the result does not depend on batch padding) and rounds to float16, the
  same precision as the fixture. Query vectors are memoised per process.

Nothing in this module is imported by the default pipeline unless
``CopilotConfig.embedding_backend`` is not ``"off"``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ops_copilot.text import split_sentences
from ops_copilot.types import Chunk

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "data" / "embeddings"
CORPUS_FIXTURE = FIXTURE_DIR / "minilm_corpus.npz"
QUERY_FIXTURE = FIXTURE_DIR / "minilm_queries.npz"
# Write-prototype backoff: lexicon prototype spans, dev calibration spans and
# the masked spans of eval queries that reach the backoff.
WRITE_FIXTURE = FIXTURE_DIR / "minilm_write.npz"
MANIFEST = FIXTURE_DIR / "manifest.json"
BACKENDS: tuple[str, ...] = ("off", "frozen", "model", "auto")


class EmbeddingUnavailable(RuntimeError):
    """The requested backend cannot run here (package or model missing)."""


def text_key(text: str) -> str:
    """Stable fixture key for an exact input string."""
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:20]


def passage_text(chunk: Chunk) -> str:
    """What the dense retriever embeds for a chunk: title, then body."""
    return f"{chunk.title}. {chunk.text}".strip()


def evidence_text(chunk: Chunk) -> str:
    """The evidence string grounding sees for a chunk (same as the lexical gate)."""
    return f"{chunk.title} {chunk.text}"


def evidence_sentences(evidence: str) -> list[str]:
    """Sentences of one chunk's evidence string, as embedded for grounding."""
    return [s for s in split_sentences(evidence) if s.strip()]


def _unit(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float64).ravel()
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


class EmbeddingBackend:
    """Shared lookup/cache logic; subclasses implement ``_encode_missing``."""

    name = "base"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._cache: dict[str, np.ndarray] = {}
        self.stats: Counter[str] = Counter()

    @property
    def dim(self) -> int:
        for v in self._cache.values():
            return int(v.shape[0])
        return 0

    def _encode_missing(self, texts: list[str]) -> list[np.ndarray | None]:
        return [None for _ in texts]

    def lookup(self, texts: Sequence[str]) -> list[np.ndarray | None]:
        """Unit vectors (float64) for each text, ``None`` where unavailable."""
        keys = [text_key(t) for t in texts]
        missing = [t for t, k in zip(texts, keys) if k not in self._cache]
        missing = list(dict.fromkeys(missing))
        if missing:
            for text, vec in zip(missing, self._encode_missing(missing)):
                if vec is not None:
                    self._cache[text_key(text)] = vec
                    self.stats["encoded"] += 1
        out: list[np.ndarray | None] = []
        for k in keys:
            vec = self._cache.get(k)
            self.stats["hit" if vec is not None else "miss"] += 1
            out.append(vec)
        return out

    def vector(self, text: str) -> np.ndarray | None:
        return self.lookup([text])[0]


def _load_npz(path: Path) -> tuple[dict[str, np.ndarray], dict]:
    with np.load(path, allow_pickle=False) as data:
        keys = [str(k) for k in data["keys"]]
        vecs = np.asarray(data["vectors"])
        meta = json.loads(str(data["meta"])) if "meta" in data.files else {}
    if vecs.dtype != np.float16:
        raise ValueError(f"{path.name}: expected float16 vectors, got {vecs.dtype}")
    return {k: _unit(v) for k, v in zip(keys, vecs)}, meta


class FrozenEmbeddings(EmbeddingBackend):
    """Committed float16 vectors; misses stay misses (no model, no download)."""

    name = "frozen"

    def __init__(self, paths: Iterable[str | Path] | None = None) -> None:
        if paths is None:
            paths = [CORPUS_FIXTURE, QUERY_FIXTURE] + ([WRITE_FIXTURE] if WRITE_FIXTURE.is_file() else [])
        paths = [Path(p) for p in paths]
        model = DEFAULT_MODEL
        loaded: dict[str, np.ndarray] = {}
        for path in paths:
            if not path.is_file():
                raise EmbeddingUnavailable(f"embedding fixture not found: {path}")
            vecs, meta = _load_npz(path)
            model = meta.get("model", model)
            loaded.update(vecs)
        super().__init__(model)
        self._cache.update(loaded)
        self.paths = paths


def model_available(model_name: str = DEFAULT_MODEL) -> bool:
    """True when sentence-transformers is installed and the model is cached locally."""
    if importlib.util.find_spec("sentence_transformers") is None:
        return False
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(model_name, local_files_only=True)
    except Exception:  # noqa: BLE001 - any failure means "not usable offline"
        return False
    return True


_MODELS: dict[tuple[str, bool], object] = {}


def _load_model(model_name: str, allow_download: bool):
    """One SentenceTransformer per (model, download policy) per process."""
    key = (model_name, allow_download)
    if key not in _MODELS:
        from sentence_transformers import SentenceTransformer

        _MODELS[key] = SentenceTransformer(
            model_name, device="cpu", local_files_only=not allow_download
        )
    return _MODELS[key]


class ModelEmbeddings(EmbeddingBackend):
    """Live sentence-transformers model, float16-rounded, batch size 1."""

    name = "model"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        allow_download: bool = False,
        document_cache: str | Path | None = CORPUS_FIXTURE,
    ) -> None:
        super().__init__(model_name)
        if importlib.util.find_spec("sentence_transformers") is None:
            raise EmbeddingUnavailable(
                "sentence-transformers is not installed; pip install -e '.[embed]'"
            )
        if not allow_download and not model_available(model_name):
            raise EmbeddingUnavailable(
                f"{model_name} is not in the local Hugging Face cache and downloads are off"
            )
        self.allow_download = allow_download
        self._model = None
        if document_cache is not None and Path(document_cache).is_file():
            vecs, meta = _load_npz(Path(document_cache))
            if meta.get("model") == model_name:
                self._cache.update(vecs)

    def _load(self):
        if self._model is None:
            self._model = _load_model(self.model_name, self.allow_download)
        return self._model

    def encode_raw(self, texts: Sequence[str]) -> np.ndarray:
        """float16 unit vectors, one forward pass per text."""
        model = self._load()
        rows = [
            model.encode([t.strip()], batch_size=1, normalize_embeddings=True)[0]
            for t in texts
        ]
        if not rows:
            return np.zeros((0, 0), dtype=np.float16)
        return np.asarray(rows, dtype=np.float32).astype(np.float16)

    def _encode_missing(self, texts: list[str]) -> list[np.ndarray | None]:
        return [_unit(v) for v in self.encode_raw(texts)]


def resolve_backend(
    kind: str,
    *,
    model_name: str = DEFAULT_MODEL,
    allow_download: bool = False,
    fixture_paths: Iterable[str | Path] | None = None,
) -> EmbeddingBackend | None:
    """``off`` -> None, ``frozen`` -> fixture, ``model`` -> live, ``auto`` -> model else fixture."""
    if kind not in BACKENDS:
        raise ValueError(f"embedding_backend must be one of {BACKENDS}, got {kind!r}")
    if kind == "off":
        return None
    if kind == "frozen":
        return FrozenEmbeddings(fixture_paths)
    if kind == "model":
        return ModelEmbeddings(model_name, allow_download=allow_download)
    if model_available(model_name):
        return ModelEmbeddings(model_name, allow_download=False)
    return FrozenEmbeddings(fixture_paths)
