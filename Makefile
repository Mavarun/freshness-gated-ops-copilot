.PHONY: test eval demo api install install-embed robustness paraphrases split embeddings calibrate embed-eval calibrate-lexicons calibrate-answer-support calibrate-passage-support secret-entropy explain-eval

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

secret-entropy:
	python scripts/run_secret_entropy_eval.py

explain-eval:
	python scripts/run_explanation_eval.py
