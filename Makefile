.PHONY: test eval demo api install

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
