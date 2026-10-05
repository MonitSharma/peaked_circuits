#!/usr/bin/env python3
"""Deterministic, cached extension of qsim-lab's P11/P12 reduced-core solver.

Original method: Dylan Neve / qsim-lab; tracker issue #251 credits Dylan Neve
and Claude (Anthropic). Source and MIT notice: README.md and LICENSE.
Performance extensions and reduced-core certification: Monit Sharma.

The structural reduction is inferred; certification applies to the reduced
core only. No expected target strings are used by this module.
"""

import argparse
import collections
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path
import time

import cotengra as ctg
from cotengra.oe import PathOptimizer
import numpy as np
import quimb.tensor as qtn

import qsimlab_original as original


class CachedGreedy(PathOptimizer):
    """Reuse greedy paths for identical ordered contraction geometries."""

    def __init__(self):
        self.paths = {}
        self.hits = 0
        self.misses = 0

    def __call__(self, inputs, output, size_dict, memory_limit=None):
        labels = {}
        def label(index):
            if index not in labels:
                labels[index] = len(labels)
            return labels[index]
        terms = tuple(tuple(label(index) for index in term) for term in inputs)
        out = tuple(label(index) for index in output)
        dims = tuple(int(size_dict[index]) for index in labels)
        key = terms, out, dims
        if key in self.paths:
            self.hits += 1
            return self.paths[key]
        self.misses += 1
        path = ctg.array_contract_path(inputs, output, size_dict,
                                      optimize='greedy', cache=False)
        self.paths[key] = path
        return path


def infer_maps(n, anchors, sections):
    grouped = collections.defaultdict(list)
    for a, b in anchors:
        centre = (a[2] + b[1]) / 2
        for si, (lo, hi) in enumerate(sections):
            if lo <= centre <= hi:
                grouped[si].append((a[0], b[0]))
    result = []
    for si, pairs in sorted(grouped.items()):
        if len(pairs) < 50:
            continue
        mapping = {}
        # Enforce both directions instead of guessing a factorial completion.
        for source, destination in pairs:
            for a, b in ((source, destination), (destination, source)):
                if a in mapping and mapping[a] != b:
                    raise ValueError(f'Conflicting anchors in section {si} for wire {a}')
                mapping[a] = b
        missing = sorted(set(range(n)) - mapping.keys())
        if len(missing) == 1:
            mapping[missing[0]] = missing[0]
        elif missing:
            raise ValueError(f'Ambiguous unanchored wires in section {si}: {missing}')
        if set(mapping.values()) != set(range(n)):
            raise ValueError(f'Non-bijective wire map in section {si}')
        if any(mapping[mapping[q]] != q for q in range(n)):
            raise ValueError(f'Non-involutive wire map in section {si}')
        result.append((si, mapping))
    if not result:
        raise ValueError('Insufficient inverse anchors for a supported reduction')
    return result


@dataclass
class Evaluation:
    probability: float
    zs: np.ndarray
    bits: str
    circuit: object
    extra_r: frozenset
    extra_p: frozenset


class CoreEvaluator:
    def __init__(self, n, matrices, wires, r0, p0, marginal_cache=True,
                 path_cache=True):
        self.n = n
        self.matrices = matrices
        self.wires = wires
        self.r0 = r0
        self.p0 = p0
        self.use_marginal_cache = marginal_cache
        self.marginals = {}
        self.optimizer = CachedGreedy() if path_cache else 'greedy'
        self.stats = {'core_evaluations': 0, 'marginal_computations': 0,
                      'marginal_cache_hits': 0, 'amplitude_computations': 0}

    def sequence(self, extra_r, extra_p):
        return ([('R', k) for k in self.r0 + sorted(extra_r)] +
                [('P', k) for k in sorted(extra_p) + self.p0])

    def cone_key(self, q, sequence):
        cone = {q}
        gates = []
        for key in reversed(sequence):
            sites = self.wires[key]
            if any(site in cone for site in sites):
                cone.update(sites)
                gates.append(key)
        return q, tuple(gates)

    def amplitude_probability(self, circuit, bits):
        self.stats['amplitude_computations'] += 1
        return float(abs(circuit.amplitude(bits, optimize=self.optimizer))**2)

    def evaluate(self, extra_r=frozenset(), extra_p=frozenset()):
        self.stats['core_evaluations'] += 1
        sequence = self.sequence(extra_r, extra_p)
        circ = qtn.Circuit(self.n)
        for key in sequence:
            circ.apply_gate_raw(self.matrices[key[1]], self.wires[key])
        zs = np.empty(self.n)
        for q in range(self.n):
            signature = self.cone_key(q, sequence) if self.use_marginal_cache else None
            if signature is not None and signature in self.marginals:
                self.stats['marginal_cache_hits'] += 1
                zs[q] = self.marginals[signature]
            else:
                value = float(np.real(circ.local_expectation(
                    np.diag([1., -1.]), (q,), optimize=self.optimizer)))
                if not np.isfinite(value) or abs(value) > 1 + 1e-9:
                    raise ArithmeticError(f'Invalid marginal on wire {q}: {value}')
                zs[q] = value
                self.stats['marginal_computations'] += 1
                if signature is not None:
                    self.marginals[signature] = value
        bits = ''.join('0' if z > 0 else '1' for z in zs)
        probability = self.amplitude_probability(circ, bits)
        return Evaluation(probability, zs, bits, circ,
                          frozenset(extra_r), frozenset(extra_p))


def select_repair(current, candidates, evaluate, growth=1.3):
    best = None
    for side, k in sorted(set(candidates)):
        trial = evaluate(current.extra_r | {k} if side == 'R' else current.extra_r,
                         current.extra_p | {k} if side == 'P' else current.extra_p)
        if trial.probability >= growth * current.probability:
            if best is None or trial.probability > best[1].probability:
                best = (side, trial, k)
    return best


def certify_peak(evaluation, probability_fn, max_ambiguous=12, atol=1e-10):
    started = time.perf_counter()
    p = evaluation.probability
    s = evaluation.bits
    minority = np.array([(1 - z if bit == '0' else 1 + z) / 2
                         for bit, z in zip(s, evaluation.zs)])
    ambiguous = np.flatnonzero(minority >= p - atol).tolist()
    report = {'scope': 'reduced_core', 'candidate_probability': p,
              'ambiguous_core_wires': ambiguous, 'numerical_tolerance': atol}
    if len(ambiguous) > max_ambiguous:
        return dict(report, status='inconclusive', reason='enumeration limit',
                    certified=False, seconds=time.perf_counter()-started)
    competitors = []
    for flips in itertools.product((False, True), repeat=len(ambiguous)):
        if not any(flips):
            continue
        candidate = list(s)
        changed = [q for q, flip in zip(ambiguous, flips) if flip]
        for q in changed:
            candidate[q] = '1' if candidate[q] == '0' else '0'
        probability = probability_fn(evaluation.circuit, ''.join(candidate))
        competitors.append({'flipped_core_wires': changed, 'probability': probability})
    outside = [q for q in range(len(s)) if q not in ambiguous]
    outside_bound = float(max((minority[q] for q in outside), default=0.0))
    competitor_bound = max([outside_bound] + [x['probability'] for x in competitors])
    certified = bool(p > competitor_bound + atol)
    return dict(report, status='unique_global_mode' if certified else 'not_certified',
                certified=certified, competitors=competitors,
                unenumerated_competitors_upper_bound=outside_bound,
                all_competitors_upper_bound=float(competitor_bound),
                seconds=time.perf_counter()-started)


def solve(path, marginal_cache=True, path_cache=True, verify_cache=False,
          max_ambiguous=12, verbose=True):
    started = time.perf_counter()
    n, units = original.parse(path)
    matrices = [original.unit_matrix(unit) for unit in units]
    secs = original.sections(units)
    if len(secs) < 3:
        raise ValueError('Insufficient supported generation sections')
    anchors = original.anchors(n, units)
    maps = infer_maps(n, anchors, secs)
    labels = list(range(n))
    for _, mapping in maps:
        labels = [labels[mapping[q]] for q in range(n)]
    wires = {}
    for k, unit in enumerate(units):
        wires['R', k] = unit[:2]
        wires['P', k] = tuple(labels[q] for q in unit[:2])
    evaluator = CoreEvaluator(n, matrices, wires,
        list(range(secs[0][0], secs[0][1]+1)),
        list(range(secs[-1][0], secs[-1][1]+1)),
        marginal_cache, path_cache)
    current = evaluator.evaluate()
    initial_probability = current.probability
    if verbose:
        print(f'{Path(path).name}: {n} qubits, {len(anchors)} anchors, '
              f'initial core probability {initial_probability:.6f}', flush=True)
    seq = collections.defaultdict(list)
    for k, unit in enumerate(units):
        for q in unit[:2]:
            seq[q].append(k)
    lo1, hi1 = secs[1]
    lo_last, hi_last = secs[-2]
    repairs = []
    while True:
        weak = {q for q, z in enumerate(current.zs) if abs(z) < 0.6}
        if not weak:
            break
        candidates = []
        for w in range(n):
            for k in seq[w]:
                if lo1 <= k <= hi1 and k not in current.extra_r:
                    a, b = units[k][:2]
                    other = b if a == w else a
                    if all(kk in current.extra_r for kk in seq[other] if lo1 <= kk < k):
                        if a in weak or b in weak:
                            candidates.append(('R', k))
                    break
            for k in reversed(seq[w]):
                if lo_last <= k <= hi_last and k not in current.extra_p:
                    a, b = units[k][:2]
                    other = b if a == w else a
                    if all(kk in current.extra_p for kk in seq[other] if k < kk <= hi_last):
                        if labels[a] in weak or labels[b] in weak:
                            candidates.append(('P', k))
                    break
        selected = select_repair(current, candidates, evaluator.evaluate)
        if selected is None:
            break
        side, current, k = selected
        repairs.append({'side': side, 'gate': k, 'probability': current.probability})
        if verbose:
            print(f'  repair {side} {k}: {current.probability:.6f}', flush=True)
    solver_seconds = time.perf_counter()-started
    solver_stats = evaluator.stats.copy()
    validation = None
    if verify_cache:
        validation_started = time.perf_counter()
        fresh = np.array([float(np.real(current.circuit.local_expectation(
            np.diag([1., -1.]), (q,), optimize='greedy'))) for q in range(n)])
        error = float(np.max(np.abs(current.zs-fresh)))
        if not np.allclose(current.zs, fresh, rtol=0, atol=1e-9):
            raise AssertionError(f'Cached marginals differ from fresh results by {error}')
        validation = {'max_absolute_marginal_error': error,
                      'seconds': time.perf_counter()-validation_started}
    certificate = certify_peak(current, evaluator.amplitude_probability, max_ambiguous)
    peak = ''.join(current.bits[labels[q]] for q in range(n))
    return {'circuit': str(Path(path).resolve()),
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'peak': peak, 'qubit_order': 'qubit 0 leftmost',
            'core_probability': current.probability,
            'initial_core_probability': initial_probability,
            'sections': secs, 'anchors': len(anchors),
            'repairs': repairs, 'solver_seconds': solver_seconds,
            'certificate': certificate, 'cache_validation': validation,
            'total_seconds': time.perf_counter()-started,
            'statistics': solver_stats,
            'path_cache': {'enabled': path_cache,
                'hits': evaluator.optimizer.hits if path_cache else 0,
                'misses': evaluator.optimizer.misses if path_cache else 0},
            'marginal_cache_enabled': marginal_cache}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('circuits', nargs='+')
    ap.add_argument('--output-dir', type=Path)
    ap.add_argument('--no-marginal-cache', action='store_true')
    ap.add_argument('--no-path-cache', action='store_true')
    ap.add_argument('--verify-cache', action='store_true')
    ap.add_argument('--max-ambiguous', type=int, default=12)
    args = ap.parse_args()
    for path in args.circuits:
        result = solve(path, not args.no_marginal_cache, not args.no_path_cache,
                       args.verify_cache, args.max_ambiguous)
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            destination = args.output_dir / (Path(path).stem + '.json')
            destination.write_text(json.dumps(result, indent=2)+'\n')
        print('RESULT '+json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
