"""Fresh, hand-written general-English synonym set (26 rows), reported separately.

``data/eval/synonym_fresh.jsonl`` paraphrases 26 golden queries with one or two
general-English swaps (``remaining -> residual``, ``status -> condition``,
``password -> passcode``) and keeps the golden label. It was written on
2026-10-06 by the author of the word-vector backoff, *after* the backoff was
built and calibrated, so it is a check of what the external resource is meant
to cover, not an unbiased benchmark. ``vocabulary_overlap`` enforces that no
swapped-in word is a dev or held-out word of the perturbation split or any
word of the eval's synonym map, so the 203-row set and its split stay
untouched and the two sets share no replacement vocabulary.

The two ops lexicons (``tag_synonyms.py``, ``wiktionary_senses.py``) were
built on 2026-10-07, a day after these rows were written, so for them this
set is blind: nobody chose a row or a lexicon entry with the other in view.
The same holds for the answer-support model (``qa_translation.py``, trained
and calibrated on 2026-10-08) and the passage classifier
(``passage_support.py``, 2026-10-10). Since the passage classifier is on by
default, every row here runs on the pre-passage default (passage classifier
off) unless its knobs switch it on, so earlier rows keep their meaning.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.pii import detect_pii
from ops_copilot.pipeline import Copilot
from ops_copilot.text import tokenize

FRESH_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_fresh.jsonl"

CONFIGS: dict[str, dict] = {
    "default (word-vector backoff off; = PR #14)": {"use_word_vector_backoff": False},
    "+ word-vector backoff (calibrated)": {"use_word_vector_backoff": True},
    "+ word-vector backoff, unknown words only": {
        "use_word_vector_backoff": True,
        "word_vector_known_words": False,
    },
    "+ corpus PPMI backoff (PR #11, for comparison)": {"use_semantic_backoff": True},
    # Ops lexicons (2026-10-07): built after this set was written, so for them
    # it is a blind check (dev-chosen settings, robustness.TAGSYN_ON / WIKTIONARY_ON).
    "+ Stack Exchange tag synonyms (dev-chosen)": {
        "use_tag_synonym_backoff": True,
        "tag_synonym_sites": "ops",
        "tag_synonym_min_sites": 3,
    },
    "+ Wiktionary computing senses (dev-chosen)": {
        "use_wiktionary_backoff": True,
        "wiktionary_min_score": 2,
    },
    "+ tag synonyms + Wiktionary + word vectors": {
        "use_tag_synonym_backoff": True,
        "tag_synonym_sites": "ops",
        "tag_synonym_min_sites": 3,
        "use_wiktionary_backoff": True,
        "wiktionary_min_score": 2,
        "use_word_vector_backoff": True,
    },
    # Answer-support model (2026-10-08): blind for this set too (dev-chosen
    # setting, robustness.ANSWER_SUPPORT_ON), alone and with the word vectors.
    "+ answer-support model (dev-chosen)": {"use_answer_support_model": True},
    "+ answer-support model + word vectors": {
        "use_answer_support_model": True,
        "use_word_vector_backoff": True,
    },
    # Passage classifier (2026-10-10): blind for this set (dev-chosen setting,
    # robustness.PASSAGE_SUPPORT_ON), alone and with the word vectors.
    "+ passage classifier (dev-chosen)": {"use_passage_support_model": True},
    "+ passage classifier + word vectors": {
        "use_passage_support_model": True,
        "use_word_vector_backoff": True,
    },
    # WordNet noun senses (2026-10-17): blind for this set (written long
    # before). Dev-chosen gate, and the scope="all" variant for comparison.
    "+ WordNet noun senses (dev-chosen, known scope)": {"use_wordnet_noun_sense": True},
    "+ WordNet noun senses, scope all, path 1": {
        "use_wordnet_noun_sense": True,
        "wordnet_scope": "all",
        "wordnet_max_path": 1,
    },
    # The lone-unknown scope was designed after seeing the scope-all row
    # above (7 fixes, 2 broken traps), so for it this set is NOT blind.
    "+ WordNet noun senses, lone scope, path 1 (not blind)": {
        "use_wordnet_noun_sense": True,
        "wordnet_scope": "lone",
        "wordnet_max_path": 1,
    },
    "+ WordNet noun senses, lone scope, path 2 fan-out 25 (not blind)": {
        "use_wordnet_noun_sense": True,
        "wordnet_scope": "lone",
        "wordnet_max_path": 2,
        "wordnet_max_fanout": 25,
    },
    # dev2 re-calibration (2026-10-19, wordnet_dev2.py): the pre-registered
    # choice; ships off (no gain on the dev2 confirm half). Not blind: the
    # lone scope was designed with this set in view (PR #23).
    "+ WordNet noun senses, dev2-chosen (lone, path 1, first sense; ships off)": {
        "use_wordnet_noun_sense": True,
        "wordnet_scope": "lone",
        "wordnet_max_path": 1,
        "wordnet_max_neighbours": 1,
        "wordnet_morphy": False,
        "wordnet_max_sense_rank": 1,
    },
    # Datamuse means-like (2026-10-20, datamuse_dev2.py): the pre-registered
    # dev2 choice; ships off (one new dev2 confirm error). Built after this
    # set was written and chosen on dev2 calib rows only, but the lone scope
    # was designed with this set in view (PR #23), so it is not fully blind.
    "+ Datamuse means-like, dev2-chosen (lone, rank<=10, 2 neighbours; ships off)": {
        "use_datamuse_ml": True,
        "datamuse_scope": "lone",
        "datamuse_max_rank": 10,
        "datamuse_max_neighbours": 2,
        "datamuse_noun_only": False,
    },
}


def load_fresh(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else FRESH_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def swapped_words(row: dict) -> set[str]:
    out: set[str] = set()
    for part in str(row["swap"]).split(","):
        out |= set(tokenize(part.split("->", 1)[1]))
    return out


def vocabulary_overlap(rows: list[dict]) -> dict[str, list[str]]:
    """Swapped-in words shared with the perturbation split / synonym map (must be empty)."""
    from ops_copilot.perturb import synonym_pairs
    from ops_copilot.synonym_split import load_split

    split = load_split()
    eval_vocab = set(split["dev_words"]) | set(split["heldout_words"])
    for _, repl in synonym_pairs():
        eval_vocab |= set(tokenize(repl))
    hits = {r["id"]: sorted(swapped_words(r) & eval_vocab) for r in rows}
    return {k: v for k, v in hits.items() if v}


def score(config: CopilotConfig, rows: list[dict]) -> dict:
    bot = Copilot(config=config)
    per_row: dict[str, str] = {}
    wrong: list[str] = []
    fail_open = spurious = raw_pii = 0
    by_gate: dict[str, dict[str, int]] = {}
    for row in rows:
        res = bot.ask(row["query"])
        got, want = res.decision.value, row["expect_decision"]
        per_row[row["id"]] = got
        g = by_gate.setdefault(want, {"n": 0, "correct": 0})
        g["n"] += 1
        g["correct"] += got == want
        raw_pii += bool(detect_pii(res.answer or ""))
        if got != want:
            wrong.append(f"{row['id']}:{want}->{got}")
            fail_open += got == "ANSWER"
            spurious += got == "PROPOSE_WRITE"
    n = len(rows)
    ans = by_gate.get("ANSWER", {"n": 0, "correct": 0})
    return {
        "n": n,
        "accuracy": (n - len(wrong)) / n if n else 0.0,
        "answer_correct": f"{ans['correct']}/{ans['n']}",
        "n_fail_open": fail_open,
        "n_spurious_write": spurious,
        "n_raw_pii_outputs": raw_pii,
        "by_gate": by_gate,
        "wrong": wrong,
        "decisions": per_row,
    }


def run_fresh_eval(base: CopilotConfig | None = None) -> dict:
    base = base or replace(CopilotConfig(), use_passage_support_model=False)
    rows = load_fresh()
    return {
        "n_rows": len(rows),
        "vocabulary_overlap": vocabulary_overlap(rows),
        "configs": {label: score(replace(base, **knobs), rows) for label, knobs in CONFIGS.items()},
    }
