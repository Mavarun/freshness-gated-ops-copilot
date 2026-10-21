.PHONY: datamuse-dev3-sweep calibrate-datamuse-dev3 datamuse-dev3-confirm dev3-eval datamuse-table calibrate-datamuse-dev2 datamuse-dev2-confirm datamuse-coverage dev2-eval wordnet-coverage calibrate-wordnet-dev2 wordnet-dev2-confirm wordnet-table calibrate-wordnet wordnet-heldout audit-heldout noun-heldout test eval demo api install install-embed robustness paraphrases split embeddings calibrate embed-eval calibrate-lexicons calibrate-answer-support calibrate-passage-support calibrate-gloss-sense calibrate-noun-gloss-sense select-passage-support passphrase-fp secret-entropy explain-eval

install:
	python -m pip install -e ".[dev,api]"

# Optional: real MiniLM model (CPU torch wheel keeps the download small).
install-embed:
	python -m pip install -e ".[dev,embed]" --extra-index-url https://download.pytorch.org/whl/cpu

test:
	pytest

eval:
	python scripts/run_eval.py

demo:
	python scripts/run_demo.py

api:
	python scripts/run_api.py

paraphrases:
	python scripts/make_paraphrase_set.py

robustness:
	python scripts/run_robustness.py

split:
	python scripts/make_synonym_split.py

# Needs [embed] and the cached model (first run: --allow-download).
embeddings:
	python scripts/precompute_embeddings.py

calibrate:
	python scripts/calibrate_semantic_grounding.py

embed-eval:
	python scripts/run_embedding_eval.py

# External ops lexicons: dev-only calibration (committed snapshot / extract only).
calibrate-lexicons:
	python scripts/calibrate_tag_synonyms.py
	python scripts/calibrate_wiktionary.py

# Answer-support (QA translation) model: dev-only calibration (committed table
# only). Rebuilding the table needs the raw pages:
#   python scripts/fetch_stackexchange_qa.py --raw-dir /tmp/se_qa_raw
#   python scripts/build_qa_translation.py --raw-dir /tmp/se_qa_raw
calibrate-answer-support:
	python scripts/calibrate_answer_support.py

# Passage-level answer support: dev-only calibration (committed classifier and
# vectors only). Rebuilding them needs the same raw pages as the QA table:
#   python scripts/build_domain_vectors.py --raw-dir /tmp/se_qa_raw
#   python scripts/build_passage_support.py --raw-dir /tmp/se_qa_raw
calibrate-passage-support:
	python scripts/calibrate_passage_support.py

# Training-recipe selection (validation questions only) and the cued-passphrase
# false-positive check; both need the raw pages (RAW=/tmp/se_qa_raw).
RAW ?= /tmp/se_qa_raw
select-passage-support:
	python scripts/select_passage_support.py --raw-dir $(RAW)

passphrase-fp:
	python scripts/run_passphrase_fp_eval.py --raw-dir $(RAW)

secret-entropy:
	python scripts/run_secret_entropy_eval.py

explain-eval:
	python scripts/run_explanation_eval.py

# Noun gloss-sense (ops noun + Wiktionary all-POS bridges): clean + dev only.
calibrate-noun-gloss-sense:
	python scripts/calibrate_noun_gloss_sense.py

# Gloss-sense (Wiktionary computing verb gloss bridges): dev-only calibration
# on clean golden + data/write/gloss_sense_dev.jsonl (no held-out rows).
calibrate-gloss-sense:
	python scripts/calibrate_gloss_sense.py

audit-heldout:
	python scripts/audit_heldout_resources.py

noun-heldout:
	python scripts/run_noun_gloss_sense_heldout.py

# WordNet 3.0 noun neighbour table (needs the nltk_data wordnet.zip, SHA-checked).
WORDNET ?= /tmp/wordnet.zip
wordnet-table:
	python scripts/build_wordnet_neighbours.py --source $(WORDNET)

# WordNet noun sense: dev-only gate calibration (clean golden + dev rows).
calibrate-wordnet:
	python scripts/calibrate_wordnet_sense.py

# WordNet noun sense: one-shot held-out arms (decision on the dev-chosen arm).
wordnet-heldout:
	python scripts/run_wordnet_heldout.py

# WordNet gate on the dev2 set (pre-registered, ops_copilot/wordnet_dev2.py):
# calibration on clean + dev + dev2 calib, then one confirm run.
calibrate-wordnet-dev2:
	python scripts/calibrate_wordnet_dev2.py

wordnet-dev2-confirm:
	python scripts/run_wordnet_dev2_confirm.py

# Post-hoc: missed noun swaps bucketed as WordNet coverage gap vs gate vs pipeline.
wordnet-coverage:
	python scripts/run_wordnet_coverage.py

# dev2 calibration set, report-only (CI step; fails only on vocabulary / split drift).
dev2-eval:
	python scripts/run_dev2_eval.py

# Datamuse means-like snapshot (corpus-word queries only; raw lists not committed).
DATAMUSE_RAW ?= /tmp/datamuse_raw
datamuse-table:
	python scripts/fetch_datamuse_ml.py --raw-dir $(DATAMUSE_RAW)
	python scripts/build_datamuse_neighbours.py --raw-dir $(DATAMUSE_RAW) --fetched-on 2026-10-20

# Datamuse gate on dev2 (pre-registered, ops_copilot/datamuse_dev2.py):
# calibration on clean + dev + dev2 calib only.
calibrate-datamuse-dev2:
	python scripts/calibrate_datamuse_dev2.py

# One shot: off vs the dev2-chosen Datamuse arm (confirm half, robustness, fresh).
datamuse-dev2-confirm:
	python scripts/run_datamuse_dev2_confirm.py

# Post-hoc: Datamuse link rank of every dev2 / fresh noun swap vs the WordNet bucket.
datamuse-coverage:
	python scripts/run_datamuse_coverage.py

# Context-gated Datamuse on dev3 (pre-registered, ops_copilot/datamuse_dev3.py):
# calibration on dev + all dev2 + dev3 calib, plus clean golden.
calibrate-datamuse-dev3:
	python scripts/calibrate_datamuse_dev3.py

# One shot: off vs the dev3-chosen context-gated arm (dev3 confirm, robustness, fresh);
# the shelved dev2-chosen WordNet / Datamuse arms are scored for the record only.
datamuse-dev3-confirm:
	python scripts/run_datamuse_dev3_confirm.py

# Changed decisions of the dev3-chosen arm on every query literal in tests/
# (a labelled trap that opens keeps the flag off).
datamuse-dev3-sweep:
	python scripts/run_datamuse_dev3_safety_sweep.py
