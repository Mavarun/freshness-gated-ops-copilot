.PHONY: audit-heldout noun-heldout test eval demo api install install-embed robustness paraphrases split embeddings calibrate embed-eval calibrate-lexicons calibrate-answer-support calibrate-passage-support calibrate-gloss-sense calibrate-noun-gloss-sense select-passage-support passphrase-fp secret-entropy explain-eval

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
