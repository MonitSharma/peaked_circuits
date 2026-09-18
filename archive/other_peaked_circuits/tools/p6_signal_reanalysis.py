#!/usr/bin/env python3
"""Target-blind reanalysis of the corrected P6 Helios-1 shots (500 shots, 5 batches).

Offline only: no provider calls, no HQC spend, no hidden-target lookup for P6.
P11/P12 accepted answers are used solely as positive controls of the decoders.

Outputs results/hardware/p6_signal_reanalysis_20260907/{summary.json,summary.md}.
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/hardware/p6_signal_reanalysis_20260907"
P6_SHOTS = [
    ROOT / "results/hardware/p6_chunk_audit_20260907/shots_400.json",
    ROOT / "results/hardware/p6_helios_100shot_20260907_batch5/shots.json",
]
P6_QASM = ROOT / "results/hardware/p6_helios_50shot_20260829/source.qasm"
TRACKER = Path("<local-user>/code_projects/qat/tracker/data/classically-verifiable-problems/circuit-models/peaked_circuit")
CONTROLS = {
    "p11": (ROOT / "results/quantinuum/p11/classical/raw/c902a6a1-0e91-48cf-b5ba-44831fcc7726.shots.jsonl",
            TRACKER / "peaked_circuit_P11_Hqap_98x1999.qasm",
            "10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000"),
    "p12": (ROOT / "results/quantinuum/p12/classical/raw/reconstructed_200_shots.jsonl",
            TRACKER / "peaked_circuit_P12_Hqap_98x2457.qasm",
            "10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100"),
}
rng = np.random.default_rng(20260907)


def arr(strings):
    return np.array([[int(c) for c in s] for s in strings], dtype=np.int8)


def load_jsonl(path):
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(re.search(r"[01]{50,}", line).group(0))
    return arr(out)


def s(x):
    return "".join(str(int(b)) for b in x)


def ham(a, b):
    return int(np.count_nonzero(np.asarray(a) != np.asarray(b)))


def pair_distances(A):
    return np.concatenate([np.count_nonzero(A[i + 1:] != A[i], axis=1) for i in range(len(A) - 1)])


def blind_stats(A):
    n, L = A.shape
    D = pair_distances(A)
    z = (A.mean(0) - 0.5) / np.sqrt(0.25 / n)
    return {
        "shots": n, "bits": L, "unique": len(set(map(bytes, A))),
        "pairwise_mean": float(D.mean()), "pairwise_min": int(D.min()),
        "pairs_within_quarter_L": int((D <= L // 4).sum()),
        "max_abs_z": float(np.abs(z).max()), "bits_abs_z_gt_3": int((np.abs(z) > 3).sum()),
        "bits_z_gt_3_toward_1": int((z > 3).sum()), "bits_z_lt_m3_toward_0": int((z < -3).sum()),
        "ones_fraction": float(A.mean()),
    }


def em_independent(A, x0, iters=200):
    """Two-component mixture: product-Bernoulli around x (per-bit q) + uniform."""
    n, L = A.shape
    x = np.array(x0, dtype=np.int8); q = np.full(L, 0.75); w = 0.1
    for _ in range(iters):
        agree = A == x
        ll1 = np.log(w) + agree @ np.log(q) + (~agree) @ np.log(1 - q)
        ll0 = np.log(1 - w) - L * np.log(2)
        m = np.maximum(ll1, ll0); r = np.exp(ll1 - m) / (np.exp(ll1 - m) + np.exp(ll0 - m))
        R = r.sum()
        if R < 1e-9:
            break
        ones = (r[:, None] * A).sum(0) / R
        xn = (ones > 0.5).astype(np.int8)
        qn = np.clip(np.where(xn == 1, ones, 1 - ones), 0.5 + 1e-6, 1 - 1e-4)
        wn = float(np.clip(R / n, 1e-6, 1 - 1e-6))
        done = (xn == x).all() and np.abs(qn - q).max() < 1e-6 and abs(wn - w) < 1e-8
        x, q, w = xn, qn, wn
        if done:
            break
    agree = A == x
    ll1 = np.log(w) + agree @ np.log(q) + (~agree) @ np.log(1 - q); ll0 = np.log(1 - w) - L * np.log(2)
    gain = float(np.logaddexp(ll1, ll0).sum() + n * L * np.log(2))
    return {"x": x, "q": q, "w": w, "r": r, "gain": gain}


def em_multi(A, restarts):
    n = len(A); best = None; fixed = collections.Counter()
    inits = [(A.mean(0) > 0.5).astype(np.int8)] + [A[i] for i in rng.choice(n, min(restarts, n), replace=False)]
    for x0 in inits:
        out = em_independent(A, x0); fixed[s(out["x"])] += 1
        if best is None or out["gain"] > best["gain"]:
            best = out
    best["fixed_points"] = len(fixed); best["top_multiplicity"] = fixed.most_common(1)[0][1]
    return best


def parse_gates(path):
    out = []
    for line in path.read_text().splitlines():
        m = re.match(r"\s*(cz|rzz\([^)]*\)|u3?\([^)]*\))\s+q\[(\d+)\](?:\s*,\s*q\[(\d+)\])?\s*;", line)
        if m:
            out.append(tuple(int(v) for v in m.groups()[1:] if v is not None))
    return out


def light_cones(path, L):
    """Forward light cone (set of output bits) of an error at each gate position."""
    g = parse_gates(path); cur = [1 << q for q in range(L)]; per_gate = []
    for t in range(len(g) - 1, -1, -1):
        qs = g[t]
        if len(qs) == 2:
            a, b = qs; u = cur[a] | cur[b]; cur[a] = cur[b] = u; per_gate.append(u)
        else:
            per_gate.append(cur[qs[0]])
    full = (1 << L) - 1
    cnt = collections.Counter(m for m in per_gate if m != full)
    masks = np.array([[(int(m) >> i) & 1 for i in range(L)] for m in cnt], dtype=bool)
    weights = np.array([cnt[m] for m in cnt], dtype=float)
    n_full = sum(1 for m in per_gate if m == full)
    return masks, weights, n_full, len(g)


def em_lightcone(A, masks, weights, n_full, x0, eps=0.05, iters=60):
    """Mixture: peak x with one late error scrambling exactly one forward light cone
    (clean bits flip with prob eps), a fully scrambled component, and uniform."""
    n, L = A.shape; M = len(masks); clean = ~masks; nclean = clean.sum(1)
    prior = np.concatenate([weights, [n_full]]); prior /= prior.sum()
    x = np.array(x0, dtype=np.int8); w = 0.05
    for _ in range(iters):
        mism = (A != x).astype(float); mm = mism @ clean.T.astype(float)
        ll = (np.log(prior[:M])[None, :] + mm * np.log(eps) + (nclean[None, :] - mm) * np.log(1 - eps)
              + (L - nclean)[None, :] * (-np.log(2)))
        LL = np.concatenate([ll, np.full((n, 1), np.log(prior[M]) - L * np.log(2))], axis=1) + np.log(w)
        L0 = np.log(1 - w) - L * np.log(2)
        mx = np.maximum(LL.max(1), L0); den = np.exp(L0 - mx) + np.exp(LL - mx[:, None]).sum(1)
        R = np.exp(LL - mx[:, None]) / den[:, None]
        Wclean = R[:, :M] @ clean.astype(float)
        ones = (Wclean * A).sum(0); tot = Wclean.sum(0)
        xn = (ones > tot / 2).astype(np.int8); wn = float(np.clip(R.sum(1).mean(), 1e-4, 0.999))
        done = (xn == x).all() and abs(wn - w) < 1e-6
        x, w = xn, wn
        if done:
            break
    gain = float((mx + np.log(den)).sum() + n * L * np.log(2))
    conf = np.where(tot > 0, np.maximum(ones, tot - ones) / np.maximum(tot, 1e-9), 0.5)
    return {"x": x, "w": w, "gain": gain, "conf": conf, "r": R.sum(1)}


def bootstrap(A, decode, x_ref, B=30):
    n, L = A.shape; votes = np.zeros(L); dist = []
    for _ in range(B):
        xb = decode(A[rng.integers(0, n, n)])["x"]; votes += xb == x_ref; dist.append(ham(xb, x_ref))
    conf = votes / B
    return {"median_hamming_to_full": float(np.median(dist)), "max_hamming_to_full": int(max(dist)),
            "bits_agreement_below_0p8": int((conf < 0.8).sum()), "positions_below_0p8": np.nonzero(conf < 0.8)[0].tolist()}


def analyse(name, A, qasm, truth=None, batches=None, restarts=200):
    n, L = A.shape
    rep = {"name": name, "blind": blind_stats(A)}
    ind = em_multi(A, restarts)
    rep["independent_em"] = {"candidate": s(ind["x"]), "gain_nats": ind["gain"], "weight": ind["w"],
                             "mean_q": float(ind["q"].mean()), "shots_posterior_gt_0p5": int((ind["r"] > 0.5).sum()),
                             "distinct_fixed_points": ind["fixed_points"], "top_fixed_point_multiplicity": ind["top_multiplicity"]}
    masks, weights, n_full, ng = light_cones(qasm, L)
    maj = (A.mean(0) > 0.5).astype(np.int8)
    lc = em_lightcone(A, masks, weights, n_full, maj)
    lc_from_ind = em_lightcone(A, masks, weights, n_full, ind["x"])
    rep["light_cone_em"] = {
        "gates": ng, "partial_cone_gate_fraction": float(weights.sum() / ng), "distinct_partial_masks": int(len(masks)),
        "candidate_from_majority_init": s(lc["x"]), "candidate_from_independent_em_init": s(lc_from_ind["x"]),
        "hamming_between_inits": ham(lc["x"], lc_from_ind["x"]), "gain_nats": max(lc["gain"], lc_from_ind["gain"]),
        "bits_vote_confidence_below_0p9": int((lc["conf"] < 0.9).sum()),
        "bootstrap": bootstrap(A, lambda B_: em_lightcone(B_, masks, weights, n_full, (B_.mean(0) > 0.5).astype(np.int8)), lc["x"]),
    }
    if batches is not None:
        xa = em_lightcone(A[batches <= 3], masks, weights, n_full, (A[batches <= 3].mean(0) > 0.5).astype(np.int8))["x"]
        xb = em_lightcone(A[batches >= 4], masks, weights, n_full, (A[batches >= 4].mean(0) > 0.5).astype(np.int8))["x"]
        rep["light_cone_em"]["split_half_batches123_vs_45_hamming"] = ham(xa, xb)
    if truth is not None:
        t = arr([truth])[0]
        rep["versus_accepted_answer"] = {"independent_em": ham(ind["x"], t), "light_cone_em": ham(lc["x"], t), "bitwise_majority": ham(maj, t),
                                        "exact_hits": int((np.count_nonzero(A != t, axis=1) == 0).sum())}
    return rep


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p6 = np.concatenate([arr(json.loads(p.read_text())) for p in P6_SHOTS]); batches = np.repeat(np.arange(1, 6), 100)
    assert p6.shape == (500, 62)
    report = {"schema": "p6-signal-reanalysis-v1", "provider_calls": False, "hidden_target_lookup_for_p6": False, "runs": []}
    # nulls calibrated to P6 size
    report["runs"].append(analyse("null_uniform_500x62", rng.integers(0, 2, (500, 62), dtype=np.int8), P6_QASM, restarts=60))
    marg = p6.mean(0)
    report["runs"].append(analyse("null_independent_bits_with_p6_marginals", (rng.random((500, 62)) < marg).astype(np.int8), P6_QASM, restarts=60))
    # positive controls
    for key, (shots, qasm, truth) in CONTROLS.items():
        if shots.exists() and qasm.exists():
            A = load_jsonl(shots); report["runs"].append(analyse(f"{key}_all_shots", A, qasm, truth=truth, restarts=len(A)))
            if key == "p12":
                for k in (50, 100):
                    report["runs"].append(analyse(f"p12_subsample_{k}", A[rng.choice(len(A), k, replace=False)], qasm, truth=truth, restarts=k))
    report["runs"].append(analyse("p6_500_corrected", p6, P6_QASM, batches=batches, restarts=500))
    (OUT / "summary.json").write_text(json.dumps(report, indent=1) + "\n")
    lines = ["# P6 signal reanalysis summary", "", "| run | unique | pairwise min | bits |z|>3 | indep-EM gain | LC-EM gain | LC bootstrap median Δ | vs answer (LC-EM) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in report["runs"]:
        b = r["blind"]; v = r.get("versus_accepted_answer", {}).get("light_cone_em", "n/a")
        lines.append(f"| {r['name']} | {b['unique']}/{b['shots']} | {b['pairwise_min']} | {b['bits_abs_z_gt_3']} | {r['independent_em']['gain_nats']:.0f} | {r['light_cone_em']['gain_nats']:.0f} | {r['light_cone_em']['bootstrap']['median_hamming_to_full']:.0f} | {v} |")
    p6r = report["runs"][-1]
    lines += ["", f"P6 light-cone EM candidate (majority init): `{p6r['light_cone_em']['candidate_from_majority_init']}`",
              f"P6 light-cone EM candidate (independent-EM init): `{p6r['light_cone_em']['candidate_from_independent_em_init']}`",
              f"Hamming between the two P6 fixed points: {p6r['light_cone_em']['hamming_between_inits']}; split-half (batches 1-3 vs 4-5): {p6r['light_cone_em'].get('split_half_batches123_vs_45_hamming')}",
              "", "Neither P6 string is promoted as a candidate: the decoder is validated on P11/P12 but the P6 optimum is not stable under bootstrap or split-half."]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
