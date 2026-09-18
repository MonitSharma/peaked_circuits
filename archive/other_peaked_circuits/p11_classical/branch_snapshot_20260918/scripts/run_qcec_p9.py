#!/usr/bin/env python3
"""Use QCEC on the exact normalized P9 circuit and a local rewritten block."""

from __future__ import annotations

import json
import time
from pathlib import Path


def main() -> None:
    from mqt import qcec

    original = Path("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
    normalized = Path("results/p11_compiler_attack/p9_exact_normalization/peaked_circuit_P9_Hqap_56x1917.normalized.qasm")
    start = time.monotonic()
    equivalent = qcec.verify(str(original), str(normalized))
    pyzx = Path("results/p11_final_campaign/p9_pyzx_reduced.qasm")
    pyzx_result = qcec.verify(str(original), str(pyzx))
    payload = {
        "original": str(original),
        "normalized": str(normalized),
        "equivalence": str(equivalent.equivalence),
        "pyzx_equivalence": str(pyzx_result.equivalence),
        "runtime_s": time.monotonic() - start,
        "verdict": "PASS" if "equivalent" in str(equivalent.equivalence).lower() and "not" not in str(equivalent.equivalence).lower() and "equivalent" in str(pyzx_result.equivalence).lower() and "not" not in str(pyzx_result.equivalence).lower() else "FAIL",
    }
    Path("results/p11_final_campaign/qcec_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
