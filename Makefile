.PHONY: test eval demo api install install-embed robustness paraphrases split

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
