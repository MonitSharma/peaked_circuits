"""Permutation-frame lowering for circuits whose native two-qubit gate is iSWAP.

The lowering is exact at the circuit level::

    iSWAP(a, b) = SWAP(a, b) CZ(a, b) (S(a) S(b))

The SWAP is represented by exchanging logical ownership of two physical sites.
This module deliberately keeps that semantic frame separate from any later MPS
or MPO routing permutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .qasm import Gate, PeakQASM


@dataclass(frozen=True)
class FrameCircuit:
    """A SWAP-free physical circuit and its final logical/site mapping."""

    n_qubits: int
    gates: tuple[Gate, ...]
    logical_to_site: tuple[int, ...]
    site_to_logical: tuple[int, ...]
    source_gate_count: int
    iswap_count: int

    def as_peak_qasm(self) -> PeakQASM:
        return PeakQASM(self.n_qubits, self.gates, ())


def lower_iswap_frame(circuit: PeakQASM) -> FrameCircuit:
    """Lower iSWAPs to S, CZ, and a classical logical/site permutation.

    Input qubit numbers are logical labels.  Output gate operands are physical
    site numbers.  A local gate on logical ``q`` is therefore applied to
    ``logical_to_site[q]`` at the point where it occurs.  For an iSWAP, the S
    gates and CZ act before the ownership swap, matching the matrix identity.
    """

    if circuit.n_qubits < 1:
        raise ValueError("circuit must contain at least one qubit")
    logical_to_site = list(range(circuit.n_qubits))
    site_to_logical = list(range(circuit.n_qubits))
    lowered: list[Gate] = []
    iswaps = 0

    for source in circuit.gates:
        physical = tuple(logical_to_site[q] for q in source.qubits)
        if source.name != "iswap":
            lowered.append(Gate(source.name, physical, source.params, source.line))
            continue
        if len(source.qubits) != 2 or source.qubits[0] == source.qubits[1]:
            raise ValueError("iSWAP requires two distinct logical qubits")
        left, right = source.qubits
        site_left, site_right = physical
        lowered.extend(
            (
                Gate("s", (site_left,), line=source.line),
                Gate("s", (site_right,), line=source.line),
                Gate("cz", (site_left, site_right), line=source.line),
            )
        )
        logical_to_site[left], logical_to_site[right] = site_right, site_left
        site_to_logical[site_left], site_to_logical[site_right] = right, left
        iswaps += 1

    return FrameCircuit(
        n_qubits=circuit.n_qubits,
        gates=tuple(lowered),
        logical_to_site=tuple(logical_to_site),
        site_to_logical=tuple(site_to_logical),
        source_gate_count=len(circuit.gates),
        iswap_count=iswaps,
    )


def physical_bitstring_to_logical(bitstring: str, logical_to_site: tuple[int, ...]) -> str:
    """Convert a physical-site bitstring into logical q0-first order."""

    if len(bitstring) != len(logical_to_site):
        raise ValueError("bitstring and mapping have different widths")
    if sorted(logical_to_site) != list(range(len(bitstring))):
        raise ValueError("logical_to_site is not a permutation")
    return "".join(bitstring[site] for site in logical_to_site)


def _format_parameter(value: float) -> str:
    return format(float(value), ".17g")


def write_frame_qasm(frame: FrameCircuit, path: str | Path) -> None:
    """Write the lowered physical circuit as OpenQASM 2 without iSWAP/SWAP."""

    lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{frame.n_qubits}];"]
    for gate in frame.gates:
        args = ",".join(f"q[{qubit}]" for qubit in gate.qubits)
        if gate.name == "u":
            if len(gate.params) != 3:
                raise ValueError("u gates must have three parameters")
            lines.append(f"u3({','.join(_format_parameter(v) for v in gate.params)}) {args};")
        elif gate.name in {"s", "sdg", "h", "x", "y", "z", "t", "tdg", "sx"}:
            lines.append(f"{gate.name} {args};")
        elif gate.name in {"cz", "cx"}:
            lines.append(f"{gate.name} {args};")
        else:
            raise ValueError(f"unsupported gate in frame QASM writer: {gate.name}")
    Path(path).write_text("\n".join(lines) + "\n")
