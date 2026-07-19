.PHONY: setup app verify clean help

PY := .venv/bin/python3
ST := .venv/bin/streamlit

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

app:
	$(ST) run app.py --server.port 8503

# No virtualenv needed: both verifiers are stdlib only, so a reviewer can run them
# on a fresh clone before installing anything.
verify:
	python3 scripts/verify_artifacts.py
	python3 scripts/verify_notebooks.py

clean:
	rm -rf __pycache__ app/__pycache__ app/pages/__pycache__ .streamlit/cache

help:
	@echo "make setup   Install presentation dependencies"
	@echo "make app     Run the Streamlit presentation"
	@echo "make verify  Recompute every artifact hash, and check the notebooks against the store"
	@echo "make clean   Remove local runtime cache"
