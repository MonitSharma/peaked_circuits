from __future__ import annotations

import pytest


qtn = pytest.importorskip("quimb.tensor")

import numpy as np

from p12_recovery.peak.native_graph import NativeGraph
from p12_recovery.peak.native_graph_state import ISWAP, NativeGraphState


def test_native_graph_state_has_only_declared_virtual_edges():
    graph = NativeGraph(3, ((0, 1), (1, 2)), {0: (0.0, 0.0), 1: (0.0, 1.0), 2: (0.0, 2.0)}, False, (5, 8), 1)
    state = NativeGraphState(graph, max_bond=4, cutoff=0.0)
    assert set(state.edge_inds) == {(0, 1), (1, 2)}
    state.apply_iswap(0, 1)
    assert state.max_bond_observed() <= 4


def test_native_graph_state_rejects_non_edge_iswap():
    graph = NativeGraph(3, ((0, 1), (1, 2)), {0: (0.0, 0.0), 1: (0.0, 1.0), 2: (0.0, 2.0)}, False, (5, 8), 1)
    state = NativeGraphState(graph, max_bond=4, cutoff=0.0)
    with pytest.raises(ValueError):
        state.apply_iswap(0, 2)
