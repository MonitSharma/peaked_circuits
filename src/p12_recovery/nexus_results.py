from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderResultValue:
    provider_name: str
    provider_index: int | None
    shot_index: int
    bit_value: int
    source_path: str


@dataclass(frozen=True)
class ParsedProviderResult:
    values: tuple[ProviderResultValue, ...]
    headers: tuple[tuple[str, ...], ...]
    metadata: tuple[tuple[str, ...], ...]
    raw_type: str

    @property
    def shot_count(self) -> int:
        return len({value.shot_index for value in self.values})

    def as_dict(self) -> dict[str, Any]:
        return {
            "values": [asdict(value) for value in self.values],
            "headers": [list(row) for row in self.headers],
            "metadata": [list(row) for row in self.metadata],
            "raw_type": self.raw_type,
            "shot_count": self.shot_count,
        }


def parse_qir_result_records(payload: str) -> ParsedProviderResult:
    """Parse Nexus labeled QIR output without relying on mapping insertion order."""
    values: list[ProviderResultValue] = []
    headers: list[tuple[str, ...]] = []
    metadata: list[tuple[str, ...]] = []
    shot = -1
    position = 0
    for line_number, line in enumerate(payload.splitlines(), start=1):
        fields = tuple(line.split("\t"))
        if not fields or not fields[0]:
            continue
        record = fields[0]
        if record == "HEADER":
            headers.append(fields[1:])
        elif record == "START":
            shot += 1
            position = 0
        elif record == "METADATA":
            metadata.append(fields[1:])
        elif record == "OUTPUT":
            if shot < 0:
                raise ValueError(f"OUTPUT before START at line {line_number}")
            if len(fields) < 4:
                raise ValueError(f"Malformed OUTPUT record at line {line_number}")
            output_type, raw_value, label = fields[1], fields[2], fields[3]
            if output_type != "RESULT":
                continue
            if raw_value not in {"0", "1"}:
                raise ValueError(f"Nonbinary RESULT value at line {line_number}")
            values.append(
                ProviderResultValue(
                    provider_name=label,
                    provider_index=position,
                    shot_index=shot,
                    bit_value=int(raw_value),
                    source_path=f"results.lines[{line_number - 1}]",
                )
            )
            position += 1
        elif record == "END" and shot < 0:
            raise ValueError(f"END before START at line {line_number}")
    if not values:
        raise ValueError("Provider result contains no RESULT output records")
    return ParsedProviderResult(tuple(values), tuple(headers), tuple(metadata), "QIRResult")


def parse_provider_result(result: Any) -> ParsedProviderResult:
    """Normalize supported qnexus QIR, mapping, and shot-record structures."""
    qir_payload = getattr(result, "results", None)
    if isinstance(qir_payload, str):
        return parse_qir_result_records(qir_payload)
    if isinstance(result, str):
        return parse_qir_result_records(result)
    if isinstance(result, Mapping):
        values: list[ProviderResultValue] = []
        for name in sorted(result, key=str):
            raw = result[name]
            sequence = raw if isinstance(raw, Sequence) and not isinstance(raw, str) else [raw]
            for shot, bit in enumerate(sequence):
                if bit not in (0, 1, False, True):
                    raise ValueError(f"Nonbinary provider value for {name}")
                values.append(
                    ProviderResultValue(str(name), None, shot, int(bit), f"{name}[{shot}]")
                )
        if not values:
            raise ValueError("Provider mapping contains no values")
        return ParsedProviderResult(tuple(values), (), (), type(result).__name__)
    raise TypeError(f"Unsupported Nexus result structure: {type(result).__name__}")


def validate_result_shape(parsed: ParsedProviderResult, *, width: int = 98) -> None:
    by_shot: dict[int, list[ProviderResultValue]] = {}
    for value in parsed.values:
        by_shot.setdefault(value.shot_index, []).append(value)
    if not by_shot:
        raise ValueError("No shots were returned")
    for shot, values in by_shot.items():
        if len(values) != width:
            raise ValueError(f"Shot {shot} has {len(values)} outputs; expected {width}")
        names = [value.provider_name for value in values]
        if len(set(names)) != width:
            raise ValueError(f"Shot {shot} contains duplicate provider fields")
    layouts = [tuple(value.provider_name for value in by_shot[shot]) for shot in sorted(by_shot)]
    if len(set(layouts)) != 1:
        raise ValueError("Provider field order differs across shots")
