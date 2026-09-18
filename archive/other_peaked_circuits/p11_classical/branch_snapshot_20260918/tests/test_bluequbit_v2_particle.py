from pathlib import Path

from p12_recovery.bluequbit.particle_sv import _merge, run_particle_circuit


def test_particle_merge_preserves_complex_sum() -> None:
    import numpy as np

    basis, alpha = _merge(np.array([1, 0, 1]), np.array([1 + 2j, 3, -1j]))
    assert basis.tolist() == [0, 1]
    assert np.allclose(alpha, [3, 1 + 1j])


def test_particle_probe_is_blind_and_hashes_fixture(tmp_path: Path) -> None:
    out = tmp_path / "particle.json"
    run_particle_circuit("tests/fixtures/p1_u_cz.qasm", 128, 1, out)
    payload = out.read_text()
    assert '"blind": true' in payload
    assert '"qasm_sha256"' in payload
