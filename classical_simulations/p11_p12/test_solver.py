import unittest
from pathlib import Path

import numpy as np
import quimb.tensor as qtn

import qsimlab_original as original
from solve_peaked_improved import (CachedGreedy, CoreEvaluator, Evaluation,
                                   certify_peak, infer_maps, select_repair)


class SolverTests(unittest.TestCase):
    def test_repair_selects_best_qualifying_candidate_and_breaks_ties_stably(self):
        current = Evaluation(.10, np.zeros(1), '0', None, frozenset(), frozenset())
        probabilities = {1: .14, 2: .17, 3: .17}
        def evaluate(extra_r, extra_p):
            k = next(iter(extra_r))
            return Evaluation(probabilities[k], np.zeros(1), '0', None,
                              frozenset(extra_r), frozenset(extra_p))
        for candidates in [[('R', 1), ('R', 2), ('R', 3)],
                           [('R', 3), ('R', 2), ('R', 1)]]:
            selected = select_repair(current, candidates, evaluate)
            self.assertEqual(selected[2], 2)
            self.assertAlmostEqual(selected[1].probability, .17)

    def test_marginal_cache_reuses_only_unchanged_causal_cones(self):
        rng = np.random.default_rng(5)
        matrices = [np.linalg.qr(rng.normal(size=(4, 4)) +
                                1j*rng.normal(size=(4, 4)))[0] for _ in range(4)]
        wires = {('R', 0): (0, 1), ('R', 1): (2, 3),
                 ('R', 2): (0, 1), ('R', 3): (1, 2)}
        cached = CoreEvaluator(4, matrices, wires, [0, 1], [], True, True)
        cached.evaluate()
        trial = cached.evaluate(frozenset({2}))
        self.assertEqual(cached.stats['marginal_computations'], 6)
        self.assertEqual(cached.stats['marginal_cache_hits'], 2)
        for extra, evaluation in [(frozenset({2}), trial),
                                 (frozenset({2, 3}), cached.evaluate(frozenset({2, 3})))]:
            fresh = CoreEvaluator(4, matrices, wires, [0, 1], [], False, False).evaluate(extra)
            np.testing.assert_allclose(evaluation.zs, fresh.zs, rtol=0, atol=1e-11)
            self.assertAlmostEqual(evaluation.probability, fresh.probability, places=11)

    def test_path_cache_handles_renamed_indices_and_distinguishes_dimensions(self):
        optimizer = CachedGreedy()
        path = optimizer([('a', 'b'), ('b', 'c')], ('a', 'c'),
                         {'a': 2, 'b': 3, 'c': 4})
        renamed = optimizer([('x', 'y'), ('y', 'z')], ('x', 'z'),
                            {'x': 2, 'y': 3, 'z': 4})
        self.assertEqual(path, renamed)
        self.assertEqual(optimizer.hits, 1)
        optimizer([('x', 'y'), ('y', 'z')], ('x', 'z'),
                  {'x': 2, 'y': 5, 'z': 4})
        self.assertEqual(optimizer.misses, 2)

    def test_certificate_rejects_marginal_vote_when_joint_mode_differs(self):
        circ = qtn.Circuit(2, psi0=qtn.MatrixProductState.from_dense(
            np.sqrt([.40, .00, .35, .25]), dims=[2, 2]))
        evaluation = Evaluation(.35, np.array([-.20, .50]), '10', circ,
                                frozenset(), frozenset())
        probability = lambda c, s: float(abs(c.amplitude(s, optimize='greedy'))**2)
        certificate = certify_peak(evaluation, probability)
        self.assertFalse(certificate['certified'])
        self.assertEqual(certificate['ambiguous_core_wires'], [0])
        self.assertAlmostEqual(certificate['all_competitors_upper_bound'], .40)

    def test_certificate_accepts_unique_mode_and_reports_enumeration_limit(self):
        evaluation = Evaluation(.70, np.array([.80, .60]), '00', None,
                                frozenset(), frozenset())
        certificate = certify_peak(evaluation, lambda *args: self.fail('No amplitude needed'))
        self.assertTrue(certificate['certified'])
        ambiguous = Evaluation(.10, np.zeros(2), '00', None, frozenset(), frozenset())
        report = certify_peak(ambiguous, lambda *args: self.fail('Limit must stop enumeration'),
                              max_ambiguous=1)
        self.assertEqual(report['status'], 'inconclusive')
        self.assertFalse(report['certified'])

    def test_maps_match_original_on_canonical_instances(self):
        for filename in ['P11.qasm', 'P12.qasm']:
            n, units = original.parse(Path(__file__).with_name(filename))
            anchors = original.anchors(n, units)
            sections = original.sections(units)
            self.assertEqual(infer_maps(n, anchors, sections),
                             original.block_maps(n, anchors, sections))


if __name__ == '__main__':
    unittest.main()
