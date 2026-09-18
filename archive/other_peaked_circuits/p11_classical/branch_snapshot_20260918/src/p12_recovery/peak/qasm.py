"""Small, strict OpenQASM 2 reader for the peak-recovery gate vocabulary.

Custom gate declarations are parsed only to register their names.  ``iswap``
is represented as one direct two-qubit operation; this is equivalent to the
declared standard decomposition and avoids silently dropping it.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Gate:
    name: str
    qubits: tuple[int, ...]
    params: tuple[float, ...] = ()
    line: int = 0


@dataclass(frozen=True)
class PeakQASM:
    n_qubits: int
    gates: tuple[Gate, ...]
    custom_gates: tuple[str, ...]


def _number(value: str) -> float:
    tree = ast.parse(value.strip().replace("pi", "math.pi"), mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Attribute,
               ast.Name, ast.Load)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError(f"unsupported parameter expression: {value!r}")
    return float(eval(compile(tree, "<qasm>", "eval"), {"__builtins__": {}, "math": math}))


_QREG = re.compile(r"qreg\s+([A-Za-z_]\w*)\[(\d+)\]")
_DECL = re.compile(r"gate\s+([A-Za-z_]\w*)\b")
_STMT = re.compile(r"([A-Za-z_]\w*)(?:\(([^)]*)\))?\s+(.+)")
_REF = re.compile(r"([A-Za-z_]\w*)\[(\d+)\]")


def parse(path: str | Path) -> PeakQASM:
    path = Path(path)
    text = path.read_text()
    qregs: dict[str, int] = {}
    custom: list[str] = []
    gates: list[Gate] = []
    in_decl = False
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("OPENQASM", "include", "creg", "measure", "barrier")):
            continue
        if line.startswith("gate "):
            match = _DECL.match(line)
            if not match:
                raise ValueError(f"invalid custom gate declaration at {path}:{line_no}")
            custom.append(match.group(1).lower())
            in_decl = "{" not in line or "}" not in line
            continue
        if in_decl:
            if "}" in line:
                in_decl = False
            continue
        match = _QREG.fullmatch(line.rstrip(";"))
        if match:
            qregs[match.group(1)] = int(match.group(2))
            continue
        match = _STMT.fullmatch(line.rstrip(";"))
        if not match:
            raise ValueError(f"unsupported QASM syntax at {path}:{line_no}: {raw}")
        name, params_text, args = match.groups()
        name = name.lower()
        refs = _REF.findall(args)
        if not refs or any(reg not in qregs for reg, _ in refs):
            raise ValueError(f"invalid qubit references at {path}:{line_no}")
        qubits = tuple(sum(qregs[r] for r, _ in refs[:i]) + int(idx) for i, (r, idx) in enumerate(refs))
        # The target files use one quantum register.  For multiple registers, offsets
        # are computed below from declaration order rather than guessed from names.
        offsets = {}
        offset = 0
        for reg, size in qregs.items():
            offsets[reg] = offset
            offset += size
        qubits = tuple(offsets[r] + int(idx) for r, idx in refs)
        params = tuple(_number(item) for item in params_text.split(",")) if params_text else ()
        canonical = "u" if name == "u3" else name
        allowed = {"u", "u2", "u1", "cz", "cx", "rzz", "iswap", "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx"}
        if canonical not in allowed:
            raise ValueError(f"unsupported gate {name!r} at {path}:{line_no}")
        expected = 2 if canonical in {"cz", "cx", "rzz", "iswap"} else 1
        if len(qubits) != expected:
            raise ValueError(f"{name} expects {expected} qubits at {path}:{line_no}")
        gates.append(Gate(canonical, qubits, params, line_no))
    if not qregs:
        raise ValueError(f"missing qreg in {path}")
    return PeakQASM(sum(qregs.values()), tuple(gates), tuple(dict.fromkeys(custom)))
