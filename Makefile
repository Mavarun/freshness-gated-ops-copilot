.PHONY: test eval demo api install robustness paraphrases

install:
	python -m pip install -e ".[dev,api]"

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
