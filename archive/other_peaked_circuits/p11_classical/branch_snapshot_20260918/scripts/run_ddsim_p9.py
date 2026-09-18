#!/usr/bin/env python3
"""Bounded MQT DDSIM P9 prefix pilot with a per-prefix watchdog."""

from __future__ import annotations

import json
import multiprocessing as mp
import time
from pathlib import Path

import psutil
from qiskit import QuantumCircuit

QASM = "data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm"
PREFIXES = (100, 200, 400, 600, 800)


def make_prefix(source: QuantumCircuit, target: int) -> QuantumCircuit:
    prefix = QuantumCircuit(source.num_qubits)
    count = 0
    for instruction in source.data:
        prefix.append(instruction.operation, [prefix.qubits[source.find_bit(qubit).index] for qubit in instruction.qubits])
        if instruction.operation.num_qubits == 2:
            count += 1
        if count >= target:
            break
    prefix.measure_all()
    return prefix


def worker(qasm: str, target: int, queue) -> None:
    from mqt import ddsim

    source = QuantumCircuit.from_qasm_file(qasm)
    prefix = make_prefix(source, target)
    start = time.monotonic()
    backend = ddsim.DDSIMProvider().get_backend("qasm_simulator")
    result = backend.run(prefix, shots=1, seed_simulator=20260821 + target).result()
    queue.put({"status": "PASS", "runtime_s": time.monotonic() - start, "counts": result.get_counts()})


def main() -> None:
    rows = []
    for target in PREFIXES:
        queue = mp.Queue()
        process = mp.Process(target=worker, args=(QASM, target, queue))
        process.start()
        start = time.monotonic()
        peak_rss = 0
        while process.is_alive():
            try:
                peak_rss = max(peak_rss, psutil.Process(process.pid).memory_info().rss)
            except psutil.Error:
                pass
            if time.monotonic() - start > 60:
                process.terminate()
                process.join(5)
                rows.append({"prefix_2q": target, "status": "TIMEOUT", "wall_clock_s": time.monotonic() - start, "peak_rss_bytes": peak_rss})
                break
            time.sleep(0.25)
        else:
            result = queue.get() if not queue.empty() else {"status": "FAILED"}
            result.update({"prefix_2q": target, "wall_clock_s": time.monotonic() - start, "peak_rss_bytes": peak_rss})
            rows.append(result)
        print(rows[-1], flush=True)
        if rows[-1]["status"] in {"TIMEOUT", "FAILED"}:
            break
    payload = {"qasm_sha256": __import__("hashlib").sha256(Path(QASM).read_bytes()).hexdigest(), "prefixes": rows, "verdict": "P9_PREFIX_TRACTABLE" if all(row["status"] == "PASS" for row in rows) and len(rows) == len(PREFIXES) else "DDSIM_PREFIX_LIMITED"}
    Path("results/p11_final_campaign/ddsim_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
