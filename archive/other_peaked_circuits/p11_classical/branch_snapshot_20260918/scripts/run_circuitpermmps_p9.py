#!/usr/bin/env python3
"""Published-style Quimb CircuitPermMPS P9 pilot at max_bond=128."""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


QASM = Path("data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm")
EXPECTED = "01101110111001100000100000001010011100101101010111110111"


def worker(queue) -> None:
    from quimb.tensor.circuit import CircuitPermMPS

    from structural.qasm_events import parse_qasm

    circuit = parse_qasm(QASM)
    sim = CircuitPermMPS(circuit.n_qubits, max_bond=128, cutoff=1e-4)
    for event in circuit.events:
        if event.gate == "u":
            sim.apply_gate("U3", params=event.params, qubits=(event.wires[0],))
        elif event.gate == "rzz":
            sim.apply_gate("RZZ", params=event.params, qubits=event.wires)
    samples = list(sim.sample(1000, seed=20260821))
    counts = Counter(samples)
    majority = counts.most_common(1)[0][0]
    queue.put({"status": "PASS", "samples": len(samples), "majority": majority, "majority_count": counts[majority], "expected_match": majority == EXPECTED, "top5": counts.most_common(5)})


def main() -> None:
    queue = mp.Queue()
    process = mp.Process(target=worker, args=(queue,))
    process.start()
    start = time.monotonic()
    peak_rss = 0
    while process.is_alive():
        try:
            peak_rss = max(peak_rss, psutil.Process(process.pid).memory_info().rss)
        except psutil.Error:
            pass
        if time.monotonic() - start > 600:
            process.terminate()
            process.join(5)
            payload = {"status": "TIMEOUT", "wall_clock_s": time.monotonic() - start, "peak_rss_bytes": peak_rss, "max_bond": 128, "samples_requested": 1000}
            break
        time.sleep(0.5)
    else:
        payload = queue.get() if not queue.empty() else {"status": "FAILED"}
        payload.update({"wall_clock_s": time.monotonic() - start, "peak_rss_bytes": peak_rss, "max_bond": 128, "cutoff": 1e-4, "samples_requested": 1000, "qasm_sha256": hashlib.sha256(QASM.read_bytes()).hexdigest(), "expected_p9": EXPECTED})
    payload["verdict"] = "P9_56_OF_56" if payload.get("expected_match") else "NO_P9_PEAK_SIGNAL"
    Path("results/p11_final_campaign/circuitpermmps_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
