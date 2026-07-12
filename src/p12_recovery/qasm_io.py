from __future__ import annotations

import importlib.metadata
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class QASMParseError(ValueError):
    pass


@dataclass(frozen=True)
class Register:
    name: str
    size: int
    offset: int


@dataclass(frozen=True)
class Operation:
    name: str
    qubits: tuple[int, ...]
    classical_bits: tuple[int, ...] = ()
    parameters: tuple[float, ...] = ()
    conditional: bool = False
    raw: str = ""


@dataclass(frozen=True)
class ParsedQASM:
    qasm_version: str
    quantum_registers: tuple[Register, ...]
    classical_registers: tuple[Register, ...]
    operations: tuple[Operation, ...]
    parser: str
    parser_version: str
    sdk_circuit: Any | None = None

    @property
    def number_of_qubits(self) -> int:
        return sum(register.size for register in self.quantum_registers)

    @property
    def number_of_classical_bits(self) -> int:
        return sum(register.size for register in self.classical_registers)


_REG = re.compile(r"^(qreg|creg)\s+([A-Za-z_]\w*)\[(\d+)]$")
_INDEX = re.compile(r"^([A-Za-z_]\w*)\[(\d+)]$")
_GATE = re.compile(r"^([A-Za-z_]\w*)(?:\((.*)\))?\s+(.+)$")


def _statements(text: str) -> list[str]:
    no_comments = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    return [item.strip() for item in no_comments.split(";") if item.strip()]


def _parameter(value: str) -> float:
    value = value.strip()
    try:
        # QASM angle expressions used here only need numeric literals and pi arithmetic.
        if re.fullmatch(r"[\d.eE+\-*/() pi]+", value):
            return float(eval(value, {"__builtins__": {}}, {"pi": math.pi}))
    except (SyntaxError, ValueError, ZeroDivisionError):
        pass
    raise QASMParseError(f"Symbolic or invalid parameter expression: {value}")


def parse_qasm_text(text: str, *, sdk_cross_check: bool = True) -> ParsedQASM:
    statements = _statements(text)
    if not statements or not statements[0].startswith("OPENQASM "):
        raise QASMParseError("Missing OPENQASM declaration")
    version = statements.pop(0).split(maxsplit=1)[1]
    qregs: list[Register] = []
    cregs: list[Register] = []
    qlookup: dict[str, Register] = {}
    clookup: dict[str, Register] = {}
    operations: list[Operation] = []
    for statement in statements:
        if statement.startswith("include "):
            continue
        register_match = _REG.fullmatch(statement)
        if register_match:
            kind, name, size_text = register_match.groups()
            target = qregs if kind == "qreg" else cregs
            lookup = qlookup if kind == "qreg" else clookup
            if name in qlookup or name in clookup:
                raise QASMParseError(f"Duplicate register name: {name}")
            register = Register(name, int(size_text), sum(item.size for item in target))
            target.append(register)
            lookup[name] = register
            continue
        conditional = statement.startswith("if(")
        if conditional:
            close = statement.find(")")
            if close < 0:
                raise QASMParseError(f"Invalid conditional: {statement}")
            statement = statement[close + 1 :].strip()
        if statement.startswith("measure "):
            source, destination = (
                item.strip() for item in statement.removeprefix("measure ").split("->")
            )
            qrefs = _expand_reference(source, qlookup)
            crefs = _expand_reference(destination, clookup)
            if len(qrefs) != len(crefs):
                raise QASMParseError("Measurement register sizes do not match")
            operations.extend(
                Operation("measure", (q,), (c,), conditional=conditional, raw=statement)
                for q, c in zip(qrefs, crefs, strict=True)
            )
            continue
        if statement.startswith("barrier "):
            barrier_qubits: list[int] = []
            for ref in statement.removeprefix("barrier ").split(","):
                barrier_qubits.extend(_expand_reference(ref.strip(), qlookup))
            operations.append(
                Operation("barrier", tuple(barrier_qubits), conditional=conditional, raw=statement)
            )
            continue
        gate_match = _GATE.fullmatch(statement)
        if not gate_match:
            raise QASMParseError(f"Unrecognized QASM statement: {statement}")
        name, params_text, arguments = gate_match.groups()
        qubits: list[int] = []
        for argument in arguments.split(","):
            refs = _expand_reference(argument.strip(), qlookup)
            if len(refs) != 1:
                raise QASMParseError(f"Register-wide gate is not supported: {statement}")
            qubits.extend(refs)
        params = tuple(_parameter(item) for item in params_text.split(",")) if params_text else ()
        operations.append(
            Operation(
                name.lower(),
                tuple(qubits),
                parameters=params,
                conditional=conditional,
                raw=statement,
            )
        )
    parsed = ParsedQASM(
        version, tuple(qregs), tuple(cregs), tuple(operations), "transparent-qasm2", "1.0"
    )
    if sdk_cross_check:
        parsed = _pytket_cross_check(text, parsed)
    return parsed


def _expand_reference(value: str, lookup: dict[str, Register]) -> list[int]:
    match = _INDEX.fullmatch(value)
    if match:
        name, index_text = match.groups()
        if name not in lookup:
            raise QASMParseError(f"Unknown register: {name}")
        index = int(index_text)
        if index >= lookup[name].size:
            raise QASMParseError(f"Register index out of range: {value}")
        return [lookup[name].offset + index]
    if value in lookup:
        register = lookup[value]
        return list(range(register.offset, register.offset + register.size))
    raise QASMParseError(f"Invalid register reference: {value}")


def _pytket_cross_check(text: str, parsed: ParsedQASM) -> ParsedQASM:
    try:
        from pytket.qasm import circuit_from_qasm_str  # type: ignore[attr-defined]
    except ImportError as exc:
        raise QASMParseError(
            "pytket is required for primary QASM loading; install the quantum extra"
        ) from exc
    try:
        circuit = circuit_from_qasm_str(text)
    except Exception as exc:
        raise QASMParseError(f"pytket rejected QASM: {type(exc).__name__}: {exc}") from exc
    if (
        circuit.n_qubits != parsed.number_of_qubits
        or circuit.n_bits != parsed.number_of_classical_bits
    ):
        raise QASMParseError("pytket and transparent parser disagree on circuit width")
    return ParsedQASM(
        parsed.qasm_version,
        parsed.quantum_registers,
        parsed.classical_registers,
        parsed.operations,
        "pytket+transparent-qasm2",
        importlib.metadata.version("pytket"),
        circuit,
    )


def load_qasm(path: Path, *, sdk_cross_check: bool = True) -> ParsedQASM:
    if not path.is_file():
        raise FileNotFoundError(f"QASM file does not exist: {path}")
    try:
        return parse_qasm_text(path.read_text(), sdk_cross_check=sdk_cross_check)
    except UnicodeDecodeError as exc:
        raise QASMParseError(f"QASM source is not valid text: {path}") from exc


def export_pytket_qasm(parsed: ParsedQASM, path: Path) -> None:
    if parsed.sdk_circuit is None:
        raise QASMParseError("No pytket circuit is available for export")
    from pytket.qasm import circuit_to_qasm  # type: ignore[attr-defined]

    path.parent.mkdir(parents=True, exist_ok=True)
    circuit_to_qasm(parsed.sdk_circuit, str(path))


def structural_signature(parsed: ParsedQASM) -> tuple[int, int, tuple[tuple[str, int], ...]]:
    counts: dict[str, int] = {}
    for operation in parsed.operations:
        name = "u" if operation.name == "u3" else operation.name
        counts[name] = counts.get(name, 0) + 1
    return parsed.number_of_qubits, parsed.number_of_classical_bits, tuple(sorted(counts.items()))
