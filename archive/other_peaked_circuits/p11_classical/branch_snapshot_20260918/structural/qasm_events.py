"""Parse peaked-circuit QASM into deterministic temporal interaction events."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from pathlib import Path

# Register may carry any name (P5 uses ``q83``), so capture it generically.
_QREG = re.compile(r"qreg\s+([a-zA-Z][a-zA-Z0-9_]*)\[(\d+)\]")
_WIRE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*\[(\d+)\]")
_GATE = re.compile(r"([a-zA-Z][a-zA-Z0-9_]*)\s*(?:\(([^)]*)\))?\s+(.+)")


def _number(expression: str) -> float:
    """Evaluate the small numeric expression grammar used by the QASM files."""
    expression = expression.strip().replace("pi", "math.pi")
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Constant,
        ast.Attribute,
        ast.Name,
        ast.Load,
    )
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError(f"unsupported QASM expression: {expression!r}")
    return float(eval(compile(tree, "<qasm>", "eval"), {"__builtins__": {}, "math": math}))


@dataclass(frozen=True)
class Event:
    index: int
    gate: str
    wires: tuple[int, ...]
    params: tuple[float, ...]
    layer: int
    q2_index: int | None
    line: int


@dataclass(frozen=True)
class CircuitEvents:
    n_qubits: int
    events: tuple[Event, ...]
    two_qubit: tuple[Event, ...]

    @property
    def n_two_qubit(self) -> int:
        return len(self.two_qubit)

    def window(self, start: int, stop: int) -> tuple[Event, ...]:
        return self.two_qubit[max(0, start) : min(self.n_two_qubit, stop)]


def parse_qasm(path: str | Path) -> CircuitEvents:
    path = Path(path)
    n_qubits: int | None = None
    events: list[Event] = []
    last_layer: dict[int, int] = {}
    q2_index = 0
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("OPENQASM", "include", "creg", "measure", "barrier")):
            continue
        # `gate NAME a,b { ... }` declarations (e.g. P8 defines iswap inline).
        if line.startswith("gate "):
            continue
        qreg = _QREG.fullmatch(line.rstrip(";"))
        if qreg:
            n_qubits = int(qreg.group(2))
            continue
        match = _GATE.fullmatch(line.rstrip(";"))
        if not match:
            raise ValueError(f"unsupported QASM syntax at {path}:{line_number}: {raw}")
        gate, parameter_text, wire_text = match.groups()
        gate = gate.lower()
        # Strip whatever register name is in use, e.g. ``q[3]`` or ``q83[3]``.
        wires = tuple(
            int(_WIRE.fullmatch(token.strip()).group(1))
            for token in wire_text.split(",")
        )
        # ``u3`` is OpenQASM 2's spelling of the same 3-parameter single-qubit
        # rotation as ``u``; normalise so downstream code has one name.
        if gate == "u3":
            gate = "u"
        if gate not in {
            "u", "cz", "rzz", "iswap",
            "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx",
        }:
            raise ValueError(f"unsupported gate {gate!r} at {path}:{line_number}")
        if gate in {"u", "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx"} and len(wires) != 1:
            raise ValueError("u must have one wire")
        if gate in {"cz", "rzz", "iswap"} and len(wires) != 2:
            raise ValueError(f"{gate} must have two wires")
        params = (
            tuple(_number(value) for value in parameter_text.split(",")) if parameter_text else ()
        )
        invalid_params = (
            (gate == "u" and len(params) != 3)
            or (gate == "rzz" and len(params) != 1)
            or (gate not in {"u", "rzz"} and params)
        )
        if invalid_params:
            raise ValueError(f"invalid parameters for {gate} at {path}:{line_number}")
        layer = max((last_layer.get(wire, 0) for wire in wires), default=0)
        for wire in wires:
            last_layer[wire] = layer + 1
        event = Event(
            len(events),
            gate,
            wires,
            params,
            layer,
            q2_index if len(wires) == 2 else None,
            line_number,
        )
        events.append(event)
        if len(wires) == 2:
            q2_index += 1
    if n_qubits is None:
        raise ValueError(f"missing qreg in {path}")
    if any(wire >= n_qubits for event in events for wire in event.wires):
        raise ValueError("QASM wire exceeds qreg width")
    return CircuitEvents(
        n_qubits, tuple(events), tuple(event for event in events if event.q2_index is not None)
    )
