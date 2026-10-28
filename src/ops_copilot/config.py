"""Frozen clock and default policy knobs.

A frozen evaluation clock keeps ages, golden labels, and CI deterministic.
Override ``now`` or ``OPS_COPILOT_NOW`` only for live demos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

EVAL_CLOCK = datetime(2026, 9, 13, 0, 0, 0, tzinfo=timezone.utc)
RNG_SEED = 42


def parse_clock(value: str | datetime | None) -> datetime:
    """Parse an ISO-8601 clock, defaulting to the frozen eval clock."""
    if value is None:
        env = os.environ.get("OPS_COPILOT_NOW")
        if env:
            return parse_clock(env)
        return EVAL_CLOCK
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class CopilotConfig:
    """Policy and retrieval knobs for a single copilot instance."""

    max_age_hours: float = 48.0
    # When True, freshness uses per-source SLAs (see config/source_slas.yaml)
    # with max_age_hours as the fallback for unknown sources. When False,
    # every source shares max_age_hours (v0 global-only behaviour).
    use_source_slas: bool = True
    source_sla_path: str | None = None
    top_k: int = 5
    min_retrieve_score: float = 1.15
    min_cosine: float = 0.08
    grounding_threshold: float = 0.52
    support_floor: float = 0.15
    hybrid_dense_weight: float = 0.30
    use_dense: bool = True
    max_answer_sentences: int = 2
    rng_seed: int = RNG_SEED
    # Disagreement routing: compare BM25 vs the dense retriever (TitleHashDenseStub,
    # or the MiniLM EmbeddingDenseRetriever when embeddings are on) top-k doc ids.
    use_disagreement_gate: bool = True
    disagreement_top_k: int = 1
    # Agreed when Jaccard >= threshold. With top_k=1, threshold=1.0 means
    # the two retrievers must share the same top doc_id.
    disagreement_jaccard_threshold: float = 1.0
    # Session cost budget: accumulate approx_cost_units per session_id.
    # When spent + this request would exceed the budget, policy emits REFUSE_BUDGET.
    # Gate applies only when a session_id is provided (API header/body or ask()).
    use_budget_gate: bool = True
    # Default allows ~2 typical hybrid+disagreement queries then trips on the 3rd.
    session_budget_cost_units: float = 5.0
    # Prompt-injection canary farm: refuse when draft echoes unjustified CNRY tokens.
    use_canary_gate: bool = True
    canary_registry_path: str | None = None
    # HITL write gate: imperative writes become PROPOSE_WRITE (pending) until human approve.
    use_hitl_write_gate: bool = True
    # Structured write-intent parser (write_intent.py). Mood detection off is
    # the "lexicon parser only" ablation (first ontology verb anywhere is an
    # instruction). Proposals need at least write_min_confidence; anything
    # write-shaped below it, or without a target, is REFUSE_AMBIGUOUS_WRITE.
    write_mood_detection: bool = True
    write_min_confidence: float = 0.65
    # Phrasal verbs and verb-independent frames (write_phrasal.py): particle
    # direction / state ("scale down", "turn off <flag>") and "<V> <key> to
    # <value>" ("set maxmemory-policy to allkeys-lru"). Off = PR #13 parser.
    write_phrasal_parser: bool = True
    # Cache-tool command verbs from their docs (ops_cli_verbs.py: flush,
    # purge, ban, invalidate -> clear_cache). Off = the leakage ablation.
    write_ops_cli_verbs: bool = True
    # Targets must be corpus-registry entities (write_targets.EntityRegistry);
    # an unseen identifier or a noun phrase is REFUSE_AMBIGUOUS_WRITE with
    # did-you-mean suggestions. Off = PR #13 (unseen identifiers at 0.85).
    write_require_registered_target: bool = True
    # Optional nearest-action-prototype backoff for "<unknown verb> <entity>"
    # instructions (write_prototypes.py). Needs an embedding backend; a no-op
    # when embedding_backend is "off". Threshold / margin from
    # scripts/calibrate_write_prototypes.py (hand-written dev verbs only).
    write_prototype_backoff: bool = False
    write_prototype_threshold: float = 0.73
    write_prototype_margin: float = 0.07
    # Ops gloss-sense backoff for unknown write verbs (gloss_sense.py): a
    # definitional graph over Wiktionary computing *verb* senses (full gloss
    # content + synonyms, not gloss heads alone). Maps bounce/reboot -> 
    # restart_service via multi-hop bridges. Offline, committed extract only.
    # Threshold / margin / hops from scripts/calibrate_gloss_sense.py (clean
    # golden + hand-written verbs only). On by default since the held-out run
    # met the pre-registered go / no-go (ANSWER/WRITE 1/12 -> 3/12, WRITE 3/3).
    use_gloss_sense_backoff: bool = True
    gloss_sense_max_hops: int = 2
    gloss_sense_min_score: float = 3.0
    gloss_sense_margin: float = 0.4
    gloss_sense_min_gloss_cosine: float = 0.5
    gloss_sense_max_neighbours: int = 2
    # Also expose gloss-sense corpus substitutes in grounding / retrieve.
    # Stays off: the verb graph rewrote scan->image and broke a clean
    # no-evidence trap. Noun read-path uses use_noun_gloss_sense instead.
    gloss_sense_grounding: bool = False
    # Ops *noun* gloss-sense backoff (noun_gloss_sense.py): all-POS Wiktionary
    # computing glosses plus a small ops-noun seed build definitional bridges
    # for read-path paraphrases (lag~latency, health~status). High
    # min_gloss_cosine (max over sense-pair centroids) rejects false bridges.
    # Thresholds from scripts/calibrate_noun_gloss_sense.py (clean + dev only).
    use_noun_gloss_sense: bool = False
    noun_gloss_sense_max_hops: int = 2
    noun_gloss_sense_min_score: float = 1.1
    noun_gloss_sense_min_gloss_cosine: float = 0.85
    noun_gloss_sense_max_neighbours: int = 2
    # Known corpus words (e.g. lag) also accept noun-sense substitutes as
    # grounding support and get them appended in the retrieval rewrite.
    noun_gloss_sense_known_words: bool = True
    # WordNet 3.0 noun-sense backoff (wordnet_senses.py): an external sense
    # inventory maps a query noun onto corpus words in the same synset, a
    # direct hyper/hyponym, or (path 2) a co-hyponym under a hypernym with at
    # most wordnet_max_fanout hyponyms. Uses the noun read-path slot (grounding
    # alts for known words + retrieval rewrite). Gate from
    # scripts/calibrate_wordnet_sense.py (clean + dev only).
    use_wordnet_noun_sense: bool = False
    wordnet_max_path: int = 0
    wordnet_max_fanout: int = 25
    wordnet_max_neighbours: int = 1
    # "known": only corpus words get WordNet alts, in grounding only (no
    # unknown-word mapping, no retrieval rewrite). "lone": as "known", plus an
    # unknown word is mapped when it is the query's only unknown content word
    # (grounding only). "all": unknown words are
    # mapped too and substitutes enter the retrieval rewrite.
    wordnet_scope: str = "known"
    # Lemmatise inflected query nouns with WordNet's morphy detachment rules
    # before the WordNet lookup (copies -> copy). Off until calibrated.
    wordnet_morphy: bool = False
    # Sense-frequency gate: only relations reached from the query word's first
    # k WordNet senses (index.noun order, most frequent first). 0 = all senses.
    wordnet_max_sense_rank: int = 0
    # Datamuse "means like" backoff (datamuse_senses.py): usage synonymy from
    # a snapshot of Datamuse ml lists queried with corpus words only (WordNet,
    # OneLook dictionaries, PPDB XXL lexical paraphrases, word2vec). A query
    # word maps onto corpus words whose list ranks it <= datamuse_max_rank.
    # Same noun read-path slot and scopes as WordNet (chained after it).
    # Gate from scripts/calibrate_datamuse_dev2.py (clean + dev + dev2 calib).
    use_datamuse_ml: bool = False
    datamuse_scope: str = "known"
    datamuse_max_rank: int = 10
    datamuse_max_neighbours: int = 1
    # Keep only results Datamuse tagged as nouns in the corpus word's list.
    datamuse_noun_only: bool = False
    # Corpus-context gate (0 = off): keep a Datamuse candidate only if one
    # corpus chunk holds it with >= k of the query's other corpus words, and
    # rank candidates by that count first. Calibrated on dev3 calib.
    datamuse_context_min: int = 0
    # Map corpus (known) words too (original behaviour). False maps only
    # unknown words. Pre-registered dev4 test (2026-10-22,
    # artifacts/datamuse_dev4_confirm.json): +3 on dev4 confirm but it answers
    # the must-refuse trap d4-37 (legal -> duty), so use_datamuse_ml stays off.
    datamuse_expand_known: bool = True
    # Word-meaning gate (0 = off): keep a Datamuse candidate only if the
    # counter-fitted vectors also call it a substitute for the query word
    # (cosine >= t; a word outside its vocabulary fails). Pre-registered on dev5 (datamuse_dev5.py).
    datamuse_sense_min: float = 0.0
    # PII/secret redaction gate: refuse unauthorized leaks; mask authorized contacts.
    use_pii_gate: bool = True
    # Typo tolerance: unknown plain words snap to a unique corpus word within
    # one edit (identifiers exact-only). Off reproduces exact-match behaviour.
    typo_tolerance: bool = True
    # Corpus-side synonym/lemma groups (synonyms.py) for grounding, retrieval
    # rewrite, and restart verbs. Off = the ablation reported in the README.
    use_synonyms: bool = True
    # Offline semantic backoff (semantic.py): a corpus PPMI/SVD embedding plus
    # char-trigram similarity maps an otherwise unplaceable query word to a
    # few corpus words, for grounding and the retrieval rewrite. Default
    # decided by the held-out synonym rows (README "Held-out synonyms").
    use_semantic_backoff: bool = False
    semantic_char_ngrams: bool = True
    semantic_min_similarity: float = 0.60
    semantic_max_neighbours: int = 1
    # Counter-fitted word-vector backoff (word_vectors.py): an external
    # synonym resource (Mrksic et al. 2016, PPDB/WordNet-constrained vectors)
    # maps a query word the corpus lacks onto at most N corpus substitutes
    # with cosine >= the threshold, for grounding and the retrieval rewrite.
    # Committed table only (data/wordvec/), no model or download. With
    # word_vector_known_words, a *known* word missing from the evidence may
    # also be supported by its substitutes. Threshold / count / scope from
    # scripts/calibrate_word_vectors.py (clean golden + dev synonym rows only).
    # Off by default: the dev-chosen setting fixed no held-out row and broke one
    # (README "External synonym resource"); it is an opt-in for general English.
    use_word_vector_backoff: bool = False
    word_vector_min_similarity: float = 0.88
    word_vector_max_neighbours: int = 1
    word_vector_known_words: bool = True
    # Stack Exchange tag-synonym backoff (tag_synonyms.py): an external,
    # ops-domain resource (community-approved tag synonyms of Server Fault,
    # Super User, Unix & Linux, DevOps, DBA, ... and Stack Overflow) maps a
    # query word the corpus lacks onto corpus words its tag cluster links to,
    # for grounding and the retrieval rewrite. Runs before the word-vector
    # backoff. Committed snapshot only (data/tagsyn/). Sites ("all" or "ops"),
    # min_sites, neighbour count and scope from
    # scripts/calibrate_tag_synonyms.py (clean golden + dev synonym rows only).
    use_tag_synonym_backoff: bool = False
    tag_synonym_sites: str = "all"
    tag_synonym_min_sites: int = 1
    tag_synonym_max_neighbours: int = 1
    tag_synonym_known_words: bool = False
    # Wiktionary computing-sense backoff (wiktionary_senses.py): senses of
    # English Wiktionary labelled computing / software / networking / ...
    # map a query word onto corpus words its domain sense lists as synonyms
    # or names in its gloss. Runs after the tag synonyms, before the word
    # vectors. Committed extract only (data/wiktionary/). min_score (2 =
    # synonyms and pointer glosses only, 1 = also the gloss head), count and
    # scope from scripts/calibrate_tag_synonyms.py (clean + dev rows only).
    use_wiktionary_backoff: bool = False
    wiktionary_min_score: int = 1
    wiktionary_max_neighbours: int = 1
    wiktionary_known_words: bool = False
    # Answer-support model (qa_translation.py): an IBM Model 1 question <-
    # answer translation table trained on outside Stack Exchange Q&A (ops
    # sites, CC BY-SA). Unlike the backoffs it is evidence-conditioned: a
    # missing plain query word counts as supported when an evidence word
    # answers it with lift >= answer_support_min_score. Committed table only
    # (data/qa/). Threshold, max terms, scope (known words too) and strictness
    # from scripts/calibrate_answer_support.py (clean golden + dev rows only).
    # Dev choice (artifacts/answer_support_calibration.md): lift >= 4.25,
    # strict, known words too, one rescued word.
    use_answer_support_model: bool = False
    answer_support_min_score: float = 4.25
    answer_support_max_terms: int = 1
    answer_support_known_words: bool = True
    answer_support_strict: bool = True
    # Passage-level answer support (passage_support.py): a logistic pair
    # classifier trained on outside Stack Exchange (title, answer) pairs, with
    # features from ops-domain PPMI-SVD vectors (data/domainvec/). It reads the
    # whole query against each evidence chunk and may vouch for up to
    # passage_support_max_terms missing plain words when P(chunk answers the
    # question) >= passage_support_min_prob. Strict (default): wh-questions
    # only, every missing word must be eligible, identifiers stay lexical, and
    # a rescued answer may not cite a page with an unjustified canary.
    # Threshold, max terms and scope from scripts/calibrate_passage_support.py
    # (clean golden + dev rows only). Dev choice
    # (artifacts/passage_support_calibration.md): P >= 0.575, strict, known
    # words too, one rescued word (calibration accuracy 0.924 -> 0.970;
    # Oct 13 retune for the length-matched classifier, plateau 0.20-0.95).
    # On by default since its one held-out run (artifacts/robustness_report.md)
    # met the pre-registered go / no-go rule: held-out 0.429 -> 0.457, no
    # fail-open, spurious write or raw PII; fresh blind set 7/26 -> 18/26.
    use_passage_support_model: bool = True
    passage_support_min_prob: float = 0.575
    passage_support_max_terms: int = 1
    passage_support_known_words: bool = True
    passage_support_strict: bool = True
    # Word-meaning check on passage rescues (off): a rescued query word must
    # also have the credited evidence word among its counter-fitted corpus
    # neighbours (cosine >= 0.50, top 5). Added 2026-10-24 after dev5 trap d5-38
    # ("What colour is the checkout_retry feature flag?") came back ANSWER in
    # the shipped default through "colour" <- "default".
    passage_support_sense_check: bool = False
    # Null-control test on passage rescues (off at 0.0): swap the rescued word
    # for each of passage_support_null_controls seeded unrelated words; rescue
    # only if at least this fraction of them scores below the real word on
    # the same passage (passage_support.null_percentile). Added 2026-10-25 for
    # the attribute traps ("What colour / flavour / price is <known page>?").
    # On (0.30, sticky) since its one-shot confirm (artifacts/passage_null_confirm.json)
    # met every pre-registered check: trap confirm opens 2 -> 0 of 18, dev5
    # confirm 8 -> 7 of 20 with no must-refuse open, held-out unchanged.
    passage_support_null_min: float = 0.30
    passage_support_null_controls: int = 100
    # Seed of the control-word sample (passage_support.control_words). 42 is
    # the seed every recorded artifact used; other seeds exist only for the
    # 2026-10-26 seed-sensitivity check (artifacts/passage_null_seeds.md).
    passage_support_null_seed: int = 42
    # Sticky veto (off): once the null test vetoes a word for a query on any
    # evidence part, no other part of the same query may rescue it. Without
    # it the rescue is retried per supporting chunk and one lucky chunk is
    # enough (artifacts/passage_null_diagnosis.md: at-22, at-25).
    passage_support_null_sticky: bool = True
    # Seed-free null test (off): score the rescued word against the *whole*
    # control pool (passage_support.pool_null_percentile, ~5,000 words) instead
    # of a 100-word seeded sample, so neither _controls nor _seed is used.
    # Added 2026-10-27 because the shipped "0 of 36 traps" held for seed 42
    # only (artifacts/passage_null_seeds.md).
    passage_support_null_pool: bool = False
    # Credited-word check on passage rescues (all off): the passage word the
    # classifier credits for a missing query word may not be an English stop
    # word (_stop), one of the _top_freq most frequent Stack Exchange vector
    # words, or a word whose _max_rank nearest neighbours lack the query word
    # (passage_support.credited_word_problems). Added 2026-10-28: the traps that
    # beat the null test ride generic credits ("taste" <- "one", "flavour" <-
    # "two"), artifacts/passage_null_overlap.md.
    # _stop on since its one-shot confirm (artifacts/credit_check_confirm.json)
    # met every pre-registered check (v3 confirm traps 0/19, no new dev7 confirm
    # error, held-out unchanged); it closes at2-01 at a calibration cost of 4 of
    # 238 rows (artifacts/credit_check_calibration.md). _top_freq / _max_rank stay off.
    passage_support_credit_stop: bool = True
    passage_support_credit_top_freq: int = 0
    passage_support_credit_max_rank: int = 0
    # Optional sentence embeddings (embeddings.py, extra "[embed]").
    # "off" keeps the offline title-hash dense stub and lexical-only grounding
    # (the CI default); "frozen" reads the committed float16 fixtures in
    # data/embeddings/ (no model needed); "model" runs all-MiniLM-L6-v2 from the
    # local Hugging Face cache; "auto" uses the model if cached, else the fixture.
    embedding_backend: str = "off"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_allow_download: bool = False
    # With a backend on: use it as the dense retriever in the disagreement gate.
    embed_dense_retriever: bool = True
    # With a backend on: semantic grounding backoff (grounding.EmbeddingSupport).
    # Threshold and max_terms come from scripts/calibrate_semantic_grounding.py
    # (clean golden + dev synonym rows only).
    embed_semantic_grounding: bool = True
    semantic_grounding_threshold: float = 0.45
    semantic_grounding_max_terms: int = 1
    # Safety tightening (README "Real embeddings"): rescue only wh-questions
    # whose every other salient term is matched lexically, and refuse a rescued
    # answer whose cited page holds an unjustified canary. Off = unsafe ablation.
    semantic_grounding_strict: bool = True
