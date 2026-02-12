PYTHON ?= python3

.PHONY: setup etl test run lint

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	pre-commit install

etl:
	$(PYTHON) -m src.etl

test:
	pytest -q

run:
	streamlit run app/Home.py

lint:
	ruff check .
