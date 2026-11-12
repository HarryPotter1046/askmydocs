PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup sample ingest serve check

setup:  ## create venv, install deps, create .env from template
	test -d $(VENV) || $(PY) -m venv $(VENV)
	$(BIN)/pip install -r requirements.txt
	test -f .env || cp .env.example .env

sample: ## generate demo PDFs into docs/
	$(BIN)/python make_sample_pdfs.py

ingest: ## embed docs/*.pdf into Supabase (safe to re-run)
	$(BIN)/python ingest.py

serve:  ## run the API + UI at http://localhost:8000
	$(BIN)/uvicorn app:app --reload

check:  ## byte-compile sources
	$(BIN)/python -m py_compile config.py ingest.py app.py make_sample_pdfs.py
