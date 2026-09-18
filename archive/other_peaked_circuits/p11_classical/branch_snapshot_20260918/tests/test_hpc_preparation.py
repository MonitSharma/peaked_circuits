from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_hpc_launcher_is_repo_relative_and_answer_blind():
    launcher = load_script("run_p11_mpo.py")
    assert launcher.ROOT == ROOT
    forwarded = launcher._remove_forwarded_flag(
        ["--max-bond", "4096", "--expected-bitstring", "leaked", "--cutoff", "0.001"],
        "--expected-bitstring",
    )
    assert forwarded == ["--max-bond", "4096", "--cutoff", "0.001"]


def test_cpu_list_parser():
    launcher = load_script("run_p11_mpo.py")
    assert launcher._parse_cpu_list("0-2,7,9-10") == {0, 1, 2, 7, 9, 10}


def test_hpc_scripts_do_not_embed_local_absolute_paths():
    for path in (ROOT / "hpc").glob("*.sh"):
        assert "/Users/" not in path.read_text()
