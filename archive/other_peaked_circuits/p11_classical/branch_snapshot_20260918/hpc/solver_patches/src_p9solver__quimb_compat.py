"""Payload copied into the pinned p9solver checkout by bootstrap_solver.sh."""

from __future__ import annotations

import numpy as np


def _qr_stabilized_numpy(x):
    Q, R = np.linalg.qr(x)
    rd = np.diagonal(R).copy()
    zero = rd == 0.0
    s = (rd + zero) / (np.abs(rd) + zero)
    Q = Q * np.conj(s).reshape(1, -1)
    R = R * s.reshape(-1, 1)
    return Q, None, R


_applied = False


def apply() -> bool:
    global _applied
    if _applied:
        return True
    try:
        from quimb.tensor import decomp

        decomp.qr_stabilized.register("numpy")(_qr_stabilized_numpy)
        decomp.qr_stabilized_numba = _qr_stabilized_numpy
        _applied = True
    except Exception:
        _applied = False
    return _applied
