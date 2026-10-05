"""Compare completed runs to published targets, after the solves finish."""

import importlib.metadata
import json
import math
from pathlib import Path
import platform


TARGETS = {
    'P11': '10101110111010011111100010110011101011101011111001010101101100001110101110010000010100001001100000',
    'P12': '10100011110010100111000100011100110001011111011100111001010110101011001001000000101000100000111100',
}


def main():
    root = Path(__file__).parent
    summaries = []
    for name, target in TARGETS.items():
        cached = json.loads((root / 'results' / f'{name}.json').read_text())
        uncached = json.loads((root / 'uncached-results' / f'{name}.json').read_text())
        assert cached['peak'] == uncached['peak'] == target, f'{name}: target mismatch'
        assert cached['sha256'] == uncached['sha256'], f'{name}: input mismatch'
        assert cached['certificate']['certified'] and uncached['certificate']['certified']
        assert cached['cache_validation']['max_absolute_marginal_error'] <= 1e-9
        assert math.isclose(cached['core_probability'], uncached['core_probability'], abs_tol=1e-10)
        cached_repairs = [(x['side'], x['gate']) for x in cached['repairs']]
        uncached_repairs = [(x['side'], x['gate']) for x in uncached['repairs']]
        assert cached_repairs == uncached_repairs, f'{name}: repair paths differ'
        assert cached['statistics']['core_evaluations'] == uncached['statistics']['core_evaluations']
        stats = cached['statistics']
        total_marginals = stats['marginal_computations'] + stats['marginal_cache_hits']
        assert total_marginals == 98 * stats['core_evaluations']
        assert uncached['statistics']['marginal_computations'] == total_marginals
        summaries.append({
            'circuit': name, 'matching_bits': 98, 'core_probability': cached['core_probability'],
            'repair_path': cached_repairs, 'solver_seconds': cached['solver_seconds'],
            'uncached_solver_seconds': uncached['solver_seconds'],
            'speedup_vs_same_search_uncached': uncached['solver_seconds']/cached['solver_seconds'],
            'certificate_seconds': cached['certificate']['seconds'],
            'solve_plus_certificate_seconds': cached['solver_seconds']+cached['certificate']['seconds'],
            'total_including_cache_validation_seconds': cached['total_seconds'],
            'marginal_reuse_percent': 100*stats['marginal_cache_hits']/total_marginals,
            'core_unique_global_mode_certified': True,
            'cache_validation_max_error': cached['cache_validation']['max_absolute_marginal_error'],
        })
    report = {
        'environment': {'python': platform.python_version(), 'architecture': platform.machine(),
                        'packages': {p: importlib.metadata.version(p)
                                     for p in ['numpy', 'scipy', 'quimb', 'cotengra']}},
        'timing_scope': 'One local run per mode; solver times exclude imports, certification, and cache validation.',
        'baseline': 'Same deterministic solver search with marginal/path caches disabled; PYTHONHASHSEED=27.',
        'certification_scope': 'Reduced core only, to numerical tolerance 1e-10.',
        'results': summaries,
    }
    text = json.dumps(report, indent=2)+'\n'
    (root / 'benchmark-summary.json').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
