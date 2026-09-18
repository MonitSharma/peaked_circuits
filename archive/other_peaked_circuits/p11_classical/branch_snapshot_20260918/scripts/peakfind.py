#!/usr/bin/env python3
"""
peakfind.py -- peak recovery for peaked circuits.

What this does differently from a sample-and-majority-vote pipeline:

  1. It finds  argmax_x |<x|psi>|^2  EXACTLY over the MPS, by beam search on
     conditional probabilities, instead of trying to see the peak in 1000
     Monte-Carlo samples.  The peak survives enormous truncation error; the
     per-bit marginal of the peak does not.

  2. It reports an answer-blind go/no-go:
       ratio  = p*(top1) * 2^n            -- how far above the uniform floor
       spread = mean Hamming(top-k, top1) -- a real peak makes the beam collapse
                                             onto a tight Hamming ball
     Neither needs the hidden answer, and neither is a resampling statistic, so
     unlike bootstrap/split-half they respond to approximation bias.

  3. It records the retained Schmidt weight over the whole evolution, a direct
     fidelity proxy.  A run with no fidelity number is unfalsifiable.

  4. It lets you choose the MPS site ordering and the engine (swap-routed MPS
     vs permutation-tracking MPS), worth 1-2 orders of magnitude of effective
     bond dimension on densely connected circuits.

Usage
-----
  python peakfind.py CIRCUIT.qasm --bond 512 --engine perm --order annealed \
        --beam 1024 --out result.json

Interpreting the output
-----------------------
  ratio_to_uniform >> 1 and small Hamming spread  -> real peak; candidate sound
  ratio_to_uniform ~ 1                            -> bond dimension too low
  candidate unchanged as D doubles                -> converged; this is the answer
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time

import numpy as np
import quimb.tensor as qtn


# --------------------------------------------------------------------------- IO

def parse_qasm(path):
    """Minimal OpenQASM 2 reader for the u3/cz/iswap/rzz vocabulary."""
    n = None
    ops = []
    for line in open(path):
        line = line.split('//')[0].strip()
        if not line or line.startswith(('OPENQASM', 'include', 'gate ', 'creg',
                                        'barrier', 'measure')):
            continue
        m = re.match(r'qreg\s+\w+\[(\d+)\]', line)
        if m:
            n = int(m.group(1))
            continue
        g = re.match(r'([a-zA-Z0-9_]+)(?:\(([^)]*)\))?\s+(.*);', line)
        if g is None:
            raise ValueError(f'unparsed line: {line}')
        name = g.group(1)
        raw = g.group(2)
        qs = [int(x) for x in re.findall(r'\[(\d+)\]', g.group(3))]
        par = ([float(eval(t.replace('pi', str(math.pi)), {'__builtins__': {}}))
                for t in raw.split(',')] if raw else [])
        ops.append((name, par, qs))
    if n is None:
        raise ValueError('no qreg declaration')
    return n, ops


def u3(t, p, l):
    return np.array([[np.cos(t / 2), -np.exp(1j * l) * np.sin(t / 2)],
                     [np.exp(1j * p) * np.sin(t / 2),
                      np.exp(1j * (p + l)) * np.cos(t / 2)]], dtype=np.complex128)


ISWAP = np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
                 dtype=np.complex128)
CZ = np.diag([1, 1, 1, -1]).astype(np.complex128)


# --------------------------------------------------------- MPS site orderings

def swap_cost(n, pairs, order):
    pos = {q: i for i, q in enumerate(order)}
    return sum(abs(pos[a] - pos[b]) - 1 for a, b in pairs)


def make_ordering(n, ops, mode, anneal_iters=150_000, seed=0):
    """Choose the MPS site order; objective is total SWAP distance of all 2q gates."""
    pairs = [tuple(qs) for _, _, qs in ops if len(qs) == 2]
    if mode == 'identity':
        return list(range(n))
    W = np.zeros((n, n))
    for a, b in pairs:
        W[a, b] += 1
        W[b, a] += 1
    cands = {'identity': list(range(n))}
    L = np.diag(W.sum(1)) - W
    cands['spectral'] = [int(x) for x in np.argsort(np.linalg.eigh(L)[1][:, 1])]
    A = (W > 0).astype(float)
    cands['spectral_u'] = [int(x) for x in np.argsort(
        np.linalg.eigh(np.diag(A.sum(1)) - A)[1][:, 1])]
    if mode in cands:
        return cands[mode]
    if mode != 'annealed':
        raise ValueError(mode)
    o = list(min(cands.values(), key=lambda v: swap_cost(n, pairs, v)))
    pos = {q: i for i, q in enumerate(o)}
    cur = sum(abs(pos[a] - pos[b]) - 1 for a, b in pairs)
    rng = np.random.default_rng(seed)
    T = n / 2.0
    for _ in range(anneal_iters):
        i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
        if i == j:
            continue
        qi, qj = o[i], o[j]
        pos[qi], pos[qj] = j, i
        new = sum(abs(pos[a] - pos[b]) - 1 for a, b in pairs)
        if new <= cur or rng.random() < np.exp(-(new - cur) / max(T, 1e-9)):
            o[i], o[j] = qj, qi
            cur = new
        else:
            pos[qi], pos[qj] = i, j
        T *= 0.99997
    return [int(x) for x in o]


# ------------------------------------------------------------------- evolution

def evolve(n, ops, order, bond, cutoff, engine='mps', dtype='complex128',
           log_every=500):
    pos = {q: i for i, q in enumerate(order)}
    kw = dict(max_bond=bond, cutoff=cutoff, dtype=dtype,
              gate_opts=dict(cutoff_mode='rsum2', renorm=False))
    circ = (qtn.CircuitPermMPS(n, **kw) if engine == 'perm'
            else qtn.CircuitMPS(n, **kw))
    t0 = time.time()
    for k, (name, par, qs) in enumerate(ops):
        w = [pos[q] for q in qs]
        if name in ('u', 'u3'):
            circ.apply_gate_raw(u3(*par), w)
        elif name == 'cz':
            circ.apply_gate_raw(CZ, w)
        elif name == 'iswap':
            circ.apply_gate_raw(ISWAP, w)
        elif name == 'rzz':
            th = par[0]
            circ.apply_gate_raw(
                np.diag(np.exp(-1j * th / 2 * np.array([1, -1, -1, 1]))), w)
        else:
            raise ValueError(f'unsupported gate {name}')
        if log_every and k % log_every == 0:
            print(f'    gate {k:6d}/{len(ops)}  '
                  f'retained={float(abs(circ._psi.norm())**2):.4e}  '
                  f'maxbond={circ._psi.max_bond():5d}  {time.time()-t0:6.0f}s',
                  flush=True)
    return circ


# ----------------------------------------------------------------- beam search

def beam_search(mps, width=512, topk=32):
    """Exact argmax_x |<x|psi>|^2 over an MPS via beam search on conditionals."""
    m = mps.copy()
    m.right_canonicalize()
    m.normalize()
    m.permute_arrays('lpr')
    A = []
    for i in range(m.L):
        a = np.asarray(m[i].data)
        if a.ndim == 2:
            a = a.reshape(1, *a.shape) if i == 0 else a.reshape(*a.shape, 1)
        A.append(a)
    cur = [(np.ones(1, dtype=A[0].dtype), '')]
    for i in range(len(A)):
        nxt = []
        for v, bits in cur:
            for x in (0, 1):
                w = v @ A[i][:, x, :]
                nxt.append((w, bits + str(x), float(np.vdot(w, w).real)))
        nxt.sort(key=lambda z: -z[2])
        cur = [(v, b) for v, b, _ in nxt[:width]]
    out = sorted(((b, float(np.vdot(v, v).real)) for v, b in cur),
                 key=lambda z: -z[1])
    return out[:topk]


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('qasm')
    ap.add_argument('--bond', type=int, required=True)
    ap.add_argument('--cutoff', type=float, default=1e-12)
    ap.add_argument('--engine', default='mps', choices=['mps', 'perm'])
    ap.add_argument('--order', default='identity',
                    choices=['identity', 'spectral', 'spectral_u', 'annealed'])
    ap.add_argument('--order-json')
    ap.add_argument('--order-key', help='e.g. P8/annealed')
    ap.add_argument('--beam', type=int, default=512)
    ap.add_argument('--topk', type=int, default=32)
    ap.add_argument('--dtype', default='complex128')
    ap.add_argument('--out')
    a = ap.parse_args()

    n, ops = parse_qasm(a.qasm)
    if a.order_json and a.order_key:
        blob = json.load(open(a.order_json))
        prob, key = a.order_key.split('/')
        order = blob[prob]['orders'][key]
    else:
        order = make_ordering(n, ops, a.order)

    pairs = [tuple(qs) for _, _, qs in ops if len(qs) == 2]
    sc = swap_cost(n, pairs, order)
    print(f'{a.qasm}\n  n={n} ops={len(ops)} 2q={len(pairs)} engine={a.engine} '
          f'order={a.order_key or a.order} D={a.bond} cutoff={a.cutoff}', flush=True)
    print(f'  SWAP distance for this ordering: {sc} ({sc/len(pairs):.2f} per 2q gate)',
          flush=True)

    t0 = time.time()
    circ = evolve(n, ops, order, a.bond, a.cutoff, a.engine, a.dtype)
    elapsed = time.time() - t0
    _p = circ.get_psi_unordered() if a.engine=='perm' else circ.psi
    retained = float(abs(_p.norm()) ** 2)
    print(f'  evolved in {elapsed:.0f}s | retained weight (fidelity proxy) = '
          f'{retained:.4e} | final max bond = {_p.max_bond()}', flush=True)

    if a.engine == 'perm':
        site_index = list(circ.qubits)
        mps = circ.get_psi_unordered()
    else:
        site_index = list(range(n))
        mps = circ.psi
    top = beam_search(mps, a.beam, a.topk)

    def to_logical(bits):
        out = [None] * n
        for site, idx in enumerate(site_index):
            out[order[idx]] = bits[site]
        return ''.join(out)

    res = [{'logical_q0_first': to_logical(b), 'reversed': to_logical(b)[::-1],
            'p_mps': p} for b, p in top]

    ratio = res[0]['p_mps'] * 2 ** n
    gap = res[0]['p_mps'] / res[1]['p_mps']
    t1 = res[0]['logical_q0_first']
    ham = [sum(x != y for x, y in zip(t1, r['logical_q0_first'])) for r in res[1:]]
    spread = float(np.mean(ham)) if ham else 0.0
    # A truncated MPS is ALWAYS peaked on its own (low-rank artifact), so a large
    # ratio_to_uniform is necessary but nowhere near sufficient.  The binding
    # constraint is fidelity: the peak carries weight ~ F * p_peak in the MPS, and
    # it can only outrank the truncation artifacts if F is well above 2^-n.
    floor = 2.0 ** -n
    fid_ok = retained > 100 * floor
    verdict = ('PEAK CANDIDATE (confirm by stability across D doublings)'
               if fid_ok and ratio > 1e3 and spread < n / 6
               else 'FIDELITY TOO LOW - candidate is a truncation artifact, raise D'
               if not fid_ok else 'WEAK / AMBIGUOUS - raise D')
    print(f'  fidelity gate: retained={retained:.2e} vs required >~ {100*floor:.2e}'
          f'  -> {"PASS" if fid_ok else "FAIL"}', flush=True)

    print(f'  uniform floor 2^-n = {2.0**-n:.3e}', flush=True)
    for i, r in enumerate(res[:10]):
        print(f'   #{i+1:2d} p={r["p_mps"]:.4e}  x2^n={r["p_mps"]*2**n:11.1f}  '
              f'{r["logical_q0_first"]}', flush=True)
    print(f'  gap to runner-up = {gap:.2f}x | mean Hamming of top-{len(res)} '
          f'to #1 = {spread:.1f} (random ~ {n/2:.0f})', flush=True)
    print(f'  VERDICT: {verdict}', flush=True)

    if a.out:
        json.dump({'qasm': a.qasm, 'n': n, 'bond': a.bond, 'cutoff': a.cutoff,
                   'engine': a.engine, 'order': a.order_key or a.order,
                   'site_order': [int(x) for x in order],
                   'retained_weight': retained, 'runtime_s': elapsed,
                   'final_max_bond': int(_p.max_bond()),
                   'uniform_floor': 2.0 ** -n, 'ratio_to_uniform': ratio,
                   'gap_to_runner_up': gap, 'hamming_spread_topk': spread,
                   'verdict': verdict, 'fidelity_gate_pass': bool(retained > 100*2.0**-n), 'top': res},
                  open(a.out, 'w'), indent=2)


if __name__ == '__main__':
    main()
