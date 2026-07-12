PYTHON := .venv/bin/python
CLI := .venv/bin/p12-recovery

.PHONY: install install-quantum lint format typecheck test test-cov doctor fetch inspect compile-dry validate synthetic-smoke synthetic-full report clean-generated milestone-1
install:
	$(PYTHON) -m pip install -e '.[dev]'
install-quantum:
	$(PYTHON) -m pip install -e '.[quantum]'
lint:
	$(PYTHON) -m ruff check .
format:
	$(PYTHON) -m ruff format .
typecheck:
	$(PYTHON) -m mypy src
test:
	$(PYTHON) -m pytest -q -m 'not hardware'
test-cov:
	$(PYTHON) -m pytest --cov --cov-report=term-missing -m 'not hardware'
doctor:
	$(CLI) doctor
fetch:
	$(CLI) fetch
inspect:
	$(CLI) inspect
compile-dry:
	$(CLI) compile --config configs/compilation.yaml
validate:
	$(CLI) validate
synthetic-smoke:
	$(CLI) synthetic --config configs/synthetic.yaml --smoke
synthetic-full:
	$(CLI) synthetic --config configs/synthetic.yaml
report:
	$(CLI) build-report
clean-generated:
	rm -rf results/inspection/* results/compilation/* results/synthetic/* results/figures/* results/manifests/*
milestone-1: doctor fetch inspect test compile-dry validate synthetic-smoke report

