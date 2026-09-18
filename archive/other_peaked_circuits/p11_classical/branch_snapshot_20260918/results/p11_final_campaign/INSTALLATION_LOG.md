# Installation and compatibility log

The existing `.venv` uses Python 3.13.7 on Apple Silicon. The documented
official package routes were used on 2026-08-20:

```text
python -m pip install -U bqskit pyzx mqt.qcec quimb cotengra
```

The install succeeded with native/ABI-compatible wheels. DDSIM was already
installed and remained at 2.5.0. The complete pip transcript is preserved in
`pip_install_primary.log`; imports and smoke tests are in
`toolchain_smoke.json` and `scripts/toolchain_smoke.py`.

Official references consulted: BQSKit installation and compile API
(github.com/BQSKit/bqskit), PyZX PyPI installation (pypi.org/project/pyzx/),
MQT QCEC installation and Python API (mqt.readthedocs.io/projects/qcec/), and
Quimb CircuitPermMPS documentation (quimb.readthedocs.io).
