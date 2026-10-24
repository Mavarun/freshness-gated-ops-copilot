"""Counter-fitted cosine for every (result word, corpus word) pair in the Datamuse table.

The word-meaning gate on Datamuse candidates (``DatamuseSense.sense_min``)
needs a *second, independent* opinion on whether query word ``q`` can stand in
for corpus word ``c``. Datamuse ``ml`` mixes synonymy with collocation
(``legal`` ranks 21st for ``duty`` because of "legal duty"), so co-occurrence
cannot be that opinion. The counter-fitted vectors (Mrksic et al., NAACL 2016;
``word_vectors.py``) can: they are Paragram-SL999 vectors pulled together on
PPDB 2.0 synonym pairs and pushed apart on WordNet / PPDB antonym pairs, so
cosine tracks substitutability (SimLex-999 rho 0.74), not topical relatedness.

The committed neighbour table ``data/wordvec/cf_neighbours.json.gz`` keeps only
each word's 5 nearest corpus words with cosine >= 0.50, so most Datamuse pairs
have no stored cosine there. This module computes the cosine of **every pair
the Datamuse table already contains** and nothing else:

- keys and candidates come from ``data/datamuse/ml_neighbours.json.gz``, which
  was built by querying corpus words only, so no eval word chose a pair;
- the value is ``round(100 * cos(q, c))`` as an int, aligned with the Datamuse
  row order of ``q``, or ``None`` when either word is outside the 65,713-word
  counter-fitted vocabulary (the gate treats ``None`` as failing).

Build: ``scripts/build_datamuse_pair_sense.py --source /tmp/cfv.zip`` (the
archive SHA-256 is checked against ``word_vectors.SOURCE_SHA256``). The output
is zero-mtime gzip, so a rebuild from the same inputs is byte-identical.
"""

from __future__ import annotations

import gzip
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ops_copilot.text import fold_token

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "datamuse"
DEFAULT_TABLE = DATA_DIR / "cf_pair_cosine.json.gz"
SCALE = 100


def build_pair_table(
    neighbours: Mapping[str, Sequence[Sequence]],
    words: Sequence[str],
    vectors: np.ndarray,
) -> dict[str, list[int | None]]:
    """Datamuse rows -> per-row ``round(100 * cos)`` (``None`` if a word is OOV).

    ``vectors`` must be L2-normalised rows aligned with ``words``.
    """
    index = {w: i for i, w in enumerate(words)}
    out: dict[str, list[int | None]] = {}
    for key in sorted(neighbours):
        qi = index.get(key)
        vals: list[int | None] = []
        for row in neighbours[key]:
            ci = index.get(str(row[0]))
            if qi is None or ci is None:
                vals.append(None)
            else:
                vals.append(int(round(SCALE * float(vectors[qi] @ vectors[ci]))))
        out[key] = vals
    return out


def dump_table(table: dict, meta: dict, path: str | Path) -> None:
    payload = json.dumps(
        {"meta": meta, "cosine": table}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())


@dataclass(frozen=True)
class PairSenseTable:
    """``cosine(q, c)`` for pairs present in the Datamuse table, else ``None``."""

    meta: dict
    pairs: dict[str, dict[str, float | None]]

    @classmethod
    def load(cls, path: str | Path | None = None, datamuse=None) -> "PairSenseTable":
        from ops_copilot.datamuse_senses import load_table as load_datamuse

        with gzip.open(Path(path) if path else DEFAULT_TABLE, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        dm = datamuse or load_datamuse()
        pairs: dict[str, dict[str, float | None]] = {}
        for key, vals in raw["cosine"].items():
            rows = dm.neighbours.get(key, ())
            if len(rows) != len(vals):
                raise ValueError(f"pair table row count for {key!r} does not match the Datamuse table")
            pairs[key] = {
                str(r[0]): (None if v is None else v / SCALE) for r, v in zip(rows, vals)
            }
        return cls(dict(raw["meta"]), pairs)

    def cosine(self, query_word: str, corpus_word: str) -> float | None:
        tok = query_word.lower()
        row = self.pairs.get(tok)
        if row is None:
            row = self.pairs.get(fold_token(tok), {})
        return row.get(corpus_word)


_TABLES: dict[str, PairSenseTable] = {}


def load_pair_table(path: str | Path | None = None) -> PairSenseTable:
    key = str(Path(path) if path else DEFAULT_TABLE)
    if key not in _TABLES:
        _TABLES[key] = PairSenseTable.load(key)
    return _TABLES[key]
