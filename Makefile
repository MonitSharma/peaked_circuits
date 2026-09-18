PYTHON := .venv/bin/python

.PHONY: verify reproduce runtime plots

verify:
	$(PYTHON) tools/verify_tracker_packages.py

reproduce:
	$(PYTHON) tools/reproduce_tracker_recovery.py

runtime:
	$(PYTHON) tools/run_tracker_classical_audit.py p11 p12

plots:
	MPLCONFIGDIR=/tmp/peaked-circuit-mpl-cache $(PYTHON) tools/generate_tracker_plots.py
