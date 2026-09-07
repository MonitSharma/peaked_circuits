import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_p6_chunks import frames

def frame(value):
    return '\n'.join(f'OUTPUT\tRESULT\t{value}\tm{i:03d}[0]' for i in reversed(range(62)))

def test_orders_by_labels_and_preserves_real_duplicates():
    assert frames(frame(1)+'END\t0\nSTART\n'+frame(1))==['1'*62]*2

def test_rejects_incomplete_frame():
    with pytest.raises(AssertionError): frames(frame(0).split('\n',1)[1])

def test_rejects_duplicate_label():
    with pytest.raises(AssertionError): frames(frame(0).replace('m061','m060'))
