from p12_recovery.bluequbit.consensus import summarize_consensus


def test_conflicting_methods_remain_unresolved():
    result = summarize_consensus({"a": ["010"], "b": ["000"]}, 3)
    assert result["unresolved"] == 1
    assert result["bits"][1]["selected_value"] is None


def test_single_method_is_only_weak_support():
    result = summarize_consensus({"sparse": ["010"]}, 3)
    assert result["weakly_supported"] == 3
    assert result["strongly_supported"] == 0
