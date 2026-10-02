"""Optional embedding backoff: nearest action prototype for an unrecognised verb.

Off by default (``CopilotConfig.write_prototype_backoff``) and only active
with an embedding backend (frozen MiniLM fixture or the live model).

When the parser meets an instruction shaped ``<unknown verb> [the] <entity>``
("please <verb> the checkout-api app") it would refuse as ambiguous. With the
backoff on, the clause is reduced to a masked span, ``"<verb> the <kind
noun>"`` ("<verb> the service"), and compared with prototype spans built
*only from the ontology lexicons*: every action contributes ``"<lexicon verb>
the <noun>"`` for its own verbs, and two contrast classes do the same with
the read verbs and the unsupported mutations. The span is accepted for an
action only if

- the nearest class is that action (not READ, not UNSUPPORTED),
- its cosine is at least ``threshold`` and beats every other class by at
  least ``margin``, and
- the action takes the entity's kind.

Threshold and margin come from ``scripts/calibrate_write_prototypes.py``,
which uses only a hand-written dev list of *other* verbs
(``data/write/prototype_dev.jsonl``: verbs that are in no lexicon and in no
held-out word list). Because prototypes and dev verbs come from lexicon and
dev vocabulary only, nothing here sees a held-out word;
``tests/test_write_ontology.py`` checks the prototype texts, and the dev list.

Masking the entity keeps the decision about the verb: MiniLM similarity of
whole queries is dominated by the shared service name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ops_copilot.write_ontology import (
    CACHE,
    CONFIG_KEY,
    FLAG,
    INCIDENT,
    ONTOLOGY,
    READ_VERBS,
    RECIPIENT,
    SECRET,
    SERVICE,
    SPEC_BY_ACTION,
    UNSUPPORTED_VERBS,
    WriteActionType,
)

READ_CLASS = "READ"
UNSUPPORTED_CLASS = "UNSUPPORTED"
DEV_SET = Path(__file__).resolve().parents[2] / "data" / "write" / "prototype_dev.jsonl"
CALIBRATION = Path(__file__).resolve().parents[2] / "artifacts" / "write_prototype_calibration.json"

KIND_NOUN: dict[str, str] = {
    SERVICE: "service",
    CACHE: "cache",
    FLAG: "flag",
    SECRET: "secret",
    CONFIG_KEY: "setting",
    RECIPIENT: "on-call",
    INCIDENT: "incident",
    "unknown": "service",
}

# Contrast classes use a fixed, sorted subset of their lexicons so the
# prototype set stays small and stable.
_READ_PROTO_VERBS = ("check", "describe", "inspect", "investigate", "monitor", "review", "show", "watch")
_UNSUPPORTED_PROTO_VERBS = ("delete", "destroy", "drain", "kill", "remove", "stop", "terminate", "wipe")
_CONTRAST_KINDS = (SERVICE, FLAG, SECRET, CONFIG_KEY, RECIPIENT, CACHE)


def span(verb: str, kind: str) -> str:
    """Masked clause the backoff embeds: ``"<verb> the <kind noun>"``."""
    return f"{verb} the {KIND_NOUN.get(kind, 'service')}"


def prototype_texts() -> dict[str, tuple[str, ...]]:
    """class -> prototype spans (actions from their own verbs and first target kind)."""
    out: dict[str, tuple[str, ...]] = {}
    for spec in ONTOLOGY:
        kinds = [k for k in spec.target_kinds[:2] if k in KIND_NOUN] or [SERVICE]
        verbs = list(spec.verbs) + list(spec.phrasal)
        out[spec.action.value] = tuple(dict.fromkeys(span(v, k) for v in verbs for k in kinds))
    assert set(_READ_PROTO_VERBS) <= READ_VERBS
    assert set(_UNSUPPORTED_PROTO_VERBS) <= UNSUPPORTED_VERBS
    out[READ_CLASS] = tuple(span(v, k) for v in _READ_PROTO_VERBS for k in _CONTRAST_KINDS)
    out[UNSUPPORTED_CLASS] = tuple(
        span(v, k) for v in _UNSUPPORTED_PROTO_VERBS for k in _CONTRAST_KINDS
    )
    return out


def all_prototype_spans() -> list[str]:
    return list(dict.fromkeys(t for texts in prototype_texts().values() for t in texts))


def load_dev_set(path: Path = DEV_SET) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_calibration(path: Path = CALIBRATION) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("chosen")


def class_scores(vec: np.ndarray, protos: dict[str, np.ndarray]) -> dict[str, float]:
    """Max cosine of ``vec`` against each class's prototype matrix."""
    return {cls: float(np.max(mat @ vec)) for cls, mat in protos.items()}


def decide(scores: dict[str, float], kind: str, threshold: float, margin: float) -> dict:
    """Accept / reject one span from its class scores (pure; used by calibration)."""
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    (best, cos), (second, cos2) = ranked[0], ranked[1]
    out = {
        "action": best,
        "cosine": round(cos, 4),
        "runner_up": second,
        "margin": round(cos - cos2, 4),
        "accepted": False,
        "confidence": round(cos, 4),
    }
    if best in (READ_CLASS, UNSUPPORTED_CLASS):
        out["why"] = f"nearest class is {best}"
    elif cos < threshold:
        out["why"] = f"cosine {cos:.2f} < threshold {threshold:.2f}"
    elif cos - cos2 < margin:
        out["why"] = f"margin {cos - cos2:.2f} over {second} < {margin:.2f}"
    elif kind not in ("unknown",) and kind not in SPEC_BY_ACTION[WriteActionType(best)].target_kinds:
        out["why"] = f"{best} does not take a {kind}"
    else:
        out["accepted"] = True
        out["why"] = "accepted"
    return out


@dataclass
class PrototypeBackoff:
    """Nearest-prototype matcher over an ``embeddings.EmbeddingBackend``."""

    backend: object
    threshold: float
    margin: float

    def __post_init__(self) -> None:
        self._protos: dict[str, np.ndarray] = {}
        for cls, texts in prototype_texts().items():
            vecs = [v for v in self.backend.lookup(list(texts)) if v is not None]
            if vecs:
                self._protos[cls] = np.vstack(vecs)
        self.available = {a.value for a in WriteActionType} <= set(self._protos)

    def match(self, verb: str, target_kind: str) -> dict | None:
        text = span(verb, target_kind)
        if not self.available:
            return {"span": text, "accepted": False, "why": "prototype vectors unavailable",
                    "action": "-", "cosine": 0.0}
        vec = self.backend.vector(text)
        if vec is None:
            return {"span": text, "accepted": False, "why": "span not in the embedding fixture",
                    "action": "-", "cosine": 0.0}
        res = decide(class_scores(vec, self._protos), target_kind, self.threshold, self.margin)
        return {"span": text} | res
