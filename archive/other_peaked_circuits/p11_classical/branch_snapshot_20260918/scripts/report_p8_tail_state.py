"""Report and optionally sample a saved P8 tail MPS without recomputing it."""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=64)
    args = parser.parse_args()
    with args.state.open("rb") as handle:
        state = pickle.load(handle)
    result = {
        "schema_version": "p8-tail-state-report.v1",
        "state": str(args.state.resolve()),
        "max_bond": int(state.max_bond()),
        "norm": float(state.norm()),
        "samples": args.samples,
        "status": "completed",
    }
    if args.samples:
        try:
            from collections import Counter

            pairs = list(state.sample(args.samples))
            counts = Counter("".join(str(bit) for bit in bits) for bits, _ in pairs)
            result.update(
                sample_unique=len(counts), sample_top_k=counts.most_common(args.top_k)
            )
        except Exception as exc:  # keep contraction metrics even if decoder fails
            result.update(status="sampling_failed", sampling_error=repr(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
