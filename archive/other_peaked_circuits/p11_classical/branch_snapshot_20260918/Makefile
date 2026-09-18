PYTHON := .venv/bin/python
CLI := .venv/bin/p12-recovery
P12_EMULATOR_SHOTS ?= 3
P12_EMULATOR_MAX_COST ?=
P12_MAPPING_CASE ?= all_zeros
P12_PILOT_SHOTS ?= 10

.PHONY: install install-quantum lint format typecheck test test-cov doctor fetch inspect compile-dry validate synthetic-smoke synthetic-full report devices devices-p12 compile-target mapping-check estimate-cost freeze-protocol public-audit export-qir validate-qir export-mapping-qir syntax-check-mappings syntax-check-p12 cost-mapping cost-p12 emulator-mapping-one emulator-mapping-all p12-emulator-pilot milestone-4-local milestone-4-remote milestone-3-local milestone-3-syntax clean-generated milestone-1 milestone-2
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
devices:
	$(CLI) devices
devices-p12:
	$(CLI) devices --only-p12-compatible
compile-target:
	$(CLI) compile --config configs/compilation.yaml --target "$(P12_QUANTINUUM_DEVICE)"
mapping-check:
	$(CLI) mapping-check --target "$(P12_QUANTINUUM_DEVICE)" --mode emulator
estimate-cost:
	$(CLI) estimate-cost --target "$(P12_QUANTINUUM_DEVICE)" --shots 20,100,250,500,1000,2000
freeze-protocol:
	$(CLI) freeze-protocol
public-audit:
	$(CLI) public-audit
export-qir:
	$(CLI) export-qir --source circuits/original/peaked_circuit_P12_Hqap_98x2457.qasm --output results/qir/p12.ll
validate-qir:
	$(CLI) validate-qir --input results/qir/p12.ll
export-mapping-qir:
	$(CLI) export-mapping-qir
syntax-check-mappings:
	$(CLI) nexus-syntax-check --target Helios-1SC --mapping-cases --submit-syntax-check
syntax-check-p12:
	$(CLI) nexus-syntax-check --target Helios-1SC --qir results/qir/p12.ll --submit-syntax-check
cost-mapping:
	$(CLI) nexus-cost --target Helios-1E --mapping-cases --shots $(P12_EMULATOR_SHOTS)
cost-p12:
	$(CLI) nexus-cost --target Helios-1E --qir results/qir/p12.ll --shots $(P12_PILOT_SHOTS)
emulator-mapping-one:
	@test -n "$(P12_EMULATOR_MAX_COST)" || (echo "P12_EMULATOR_MAX_COST is required"; exit 2)
	$(CLI) emulator-mapping-check --target Helios-1E --mapping-case $(P12_MAPPING_CASE) --shots $(P12_EMULATOR_SHOTS) --max-cost $(P12_EMULATOR_MAX_COST) --execute-emulator
emulator-mapping-all:
	@test -n "$(P12_EMULATOR_MAX_COST)" || (echo "P12_EMULATOR_MAX_COST is required"; exit 2)
	$(CLI) emulator-mapping-check --target Helios-1E --shots $(P12_EMULATOR_SHOTS) --max-cost $(P12_EMULATOR_MAX_COST) --execute-emulator
p12-emulator-pilot:
	@test -n "$(P12_EMULATOR_MAX_COST)" || (echo "P12_EMULATOR_MAX_COST is required"; exit 2)
	$(CLI) p12-emulator-pilot --target Helios-1E --shots $(P12_PILOT_SHOTS) --max-cost $(P12_EMULATOR_MAX_COST) --execute-emulator
clean-generated:
	rm -rf results/inspection/* results/compilation/* results/synthetic/* results/figures/* results/manifests/*
milestone-1: doctor fetch inspect test compile-dry validate synthetic-smoke report
milestone-2: test lint typecheck
	$(CLI) schemas --check
	@if [ -n "$$P12_QUANTINUUM_DEVICE" ]; then $(CLI) devices --only-p12-compatible; $(CLI) compile --config configs/compilation.yaml; $(CLI) mapping-check --target "$$P12_QUANTINUUM_DEVICE" --mode emulator; $(CLI) estimate-cost --target "$$P12_QUANTINUUM_DEVICE" --shots 20,100,250,500,1000,2000; else echo "No target configured; live steps skipped"; fi
	$(CLI) build-report
	$(CLI) public-audit
milestone-3-local: export-qir validate-qir export-mapping-qir public-audit test lint typecheck
	$(CLI) schemas --check
milestone-3-syntax: milestone-3-local syntax-check-mappings syntax-check-p12
milestone-4-local: test lint typecheck public-audit
	$(CLI) schemas --check
	$(CLI) build-report
milestone-4-remote:
	@test "$$P12_ENABLE_HELIOS_EMULATOR" = "1" || (echo "P12_ENABLE_HELIOS_EMULATOR=1 is required"; exit 2)
	@test -n "$(P12_EMULATOR_MAX_COST)" || (echo "P12_EMULATOR_MAX_COST is required"; exit 2)
	$(MAKE) cost-mapping emulator-mapping-all P12_EMULATOR_MAX_COST=$(P12_EMULATOR_MAX_COST)
