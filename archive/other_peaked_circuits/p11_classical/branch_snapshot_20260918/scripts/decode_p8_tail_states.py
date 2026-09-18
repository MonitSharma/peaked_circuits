"""Decode saved P8 tail MPS states with the certified best-first MAP search."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from p12_recovery.peak.mps import best_first_map
except ModuleNotFoundError:
    # The HPC campaign checkout can intentionally lag the research branch.
    # In that case mps.py is copied beside this script for a self-contained
    # decoder, without changing the active checkout.
    from mps_decoder import best_first_map


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Saved state label and pickle path, repeated once per bond limit.",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-nodes", type=int, default=None)
    parser.add_argument("--max-seconds", type=float, default=None)
    return parser


def _parse_states(values: list[str]) -> list[tuple[str, Path]]:
    states = []
    for value in values:
        if "=" not in value:
            raise SystemExit(f"state must be LABEL=PATH, got {value!r}")
        label, path = value.split("=", 1)
        states.append((label, Path(path)))
    return states


def _arrays(state):
    """Right-canonicalize and extract tensors in (left, physical, right) order."""
    state = state.copy()
    original_norm = float(state.norm())
    state.right_canonize()
    canonical_norm = float(state.norm())
    if canonical_norm == 0:
        raise ValueError("saved state has zero norm")
    state.tensors[0].modify(data=state.tensors[0].data / canonical_norm)
    standard = []
    extra_sites = {}
    for index, tensor in enumerate(state.tensors):
        data = np.asarray(tensor.data)
        inds = list(tensor.inds)
        physical = state.site_ind(index)
        left = state.bond(index - 1, index) if index else None
        right = state.bond(index, index + 1) if index + 1 < len(state.tensors) else None
        base = [name for name in (left, physical, right) if name is not None]
        extras = [name for name in inds if name not in base]
        for name in extras:
            extra_sites.setdefault(name, []).append(index)
        order = base + extras
        if any(name not in inds for name in order):
            raise ValueError(f"tensor {index} does not expose expected MPS indices")
        data = data.transpose(*(inds.index(name) for name in order))
        standard.append((data, left is not None, right is not None, extras))

    if any(len(sites) != 2 for sites in extra_sites.values()):
        raise ValueError(f"unsupported nonlocal MPS bonds: {extra_sites}")
    if len(extra_sites) > 1:
        raise ValueError(f"multiple nonlocal MPS bonds are not supported: {extra_sites}")

    tensors = []
    crossing = next(iter(extra_sites.items()), None)
    for index, (data, has_left, has_right, extras) in enumerate(standard):
        is_crossing_middle = (
            crossing is not None
            and crossing[1][0] < index < crossing[1][1]
        )
        if not extras and not is_crossing_middle:
            if not has_left:
                data = data.reshape(1, *data.shape)
            if not has_right:
                data = data.reshape(*data.shape, 1)
            tensors.append(data)
            continue
        name, sites = crossing
        if extras not in ([], [name]):
            raise ValueError("unexpected extra-bond layout")
        start, end = sites
        if index == start:
            if not has_left:
                data = data.reshape(1, *data.shape)
            # Carry the crossing index on the outgoing chain bond.
            tensors.append(data.reshape(data.shape[0], data.shape[1], -1))
        elif index == end:
            if not has_right:
                data = data.reshape(*data.shape, 1)
            # Bring the crossing index onto the incoming chain bond.
            data = data.transpose(3, 0, 1, 2)
            tensors.append(data.reshape(-1, data.shape[2], data.shape[3]))
        elif start < index < end:
            if not has_left:
                data = data.reshape(1, *data.shape)
            if not has_right:
                data = data.reshape(*data.shape, 1)
            size = data.shape[-1]
            eye = np.eye(size, dtype=data.dtype)
            carried = np.einsum("lpr,ab->laprb", data, eye)
            tensors.append(carried.reshape(data.shape[0] * size, data.shape[1], -1))
        else:
            raise ValueError("nonlocal bond endpoints are not ordered")
    return original_norm, canonical_norm, tensors, int(state.max_bond())


def _hamming(left: str | None, right: str | None) -> int | None:
    if left is None or right is None or len(left) != len(right):
        return None
    return sum(a != b for a, b in zip(left, right, strict=True))


def main() -> int:
    args = _parser().parse_args()
    import pickle

    results = []
    for label, path in _parse_states(args.state):
        started = time.monotonic()
        with path.open("rb") as handle:
            state = pickle.load(handle)
        original_norm, canonical_norm, tensors, state_max_bond = _arrays(state)
        decoded = best_first_map(
            tensors, max_nodes=args.max_nodes, max_seconds=args.max_seconds
        )
        result = {
            "label": label,
            "state": str(path.resolve()),
            "original_norm": original_norm,
            "canonical_norm_before_rescale": canonical_norm,
            "state_max_bond": state_max_bond,
            "map_bitstring_raw_mps_site_order": decoded.bitstring,
            "map_probability": decoded.probability,
            "certified": decoded.certified,
            "nodes_expanded": decoded.nodes_expanded,
            "max_queue_size": decoded.max_queue_size,
            "queue_upper_bound": decoded.final_upper_bound,
            "runner_up": decoded.runner_up,
            "decoder_wall_time_s": decoded.wall_time_s,
            "total_wall_time_s": time.monotonic() - started,
        }
        results.append(result)

    by_label = {row["label"]: row for row in results}
    for left, right, key in (
        ("D256", "D512", "hamming_D256_D512"),
        ("D512", "D1024", "hamming_D512_D1024"),
    ):
        if left in by_label and right in by_label:
            by_label[right][key] = _hamming(
                by_label[left]["map_bitstring_raw_mps_site_order"],
                by_label[right]["map_bitstring_raw_mps_site_order"],
            )
    output = {"schema_version": "p8-tail-map-decoder.v1", "states": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
