from types import SimpleNamespace

from investigator.metrics import count_tool_calls, estimate_cost


def test_estimate_cost_for_gpt_6_luna() -> None:
    # 1000 uncached input + 1000 output, prices $0.10 and $0.50 per 1M tokens.
    assert estimate_cost("gpt-6-luna", 1000, 0, 0, 1000) == 0.0006


def test_estimate_cost_unknown_model_returns_none() -> None:
    assert estimate_cost("not-a-model", 1000, 0, 0, 1000) is None


def test_count_tool_calls_counts_asks_not_replies() -> None:
    items = [
        SimpleNamespace(type="tool_call_item", tool_name="read_file"),
        SimpleNamespace(type="tool_call_output_item", tool_name="read_file"),
        SimpleNamespace(type="tool_call_item", tool_name="read_file"),
        SimpleNamespace(type="tool_call_item", tool_name="search_code"),
        SimpleNamespace(type="message_output_item", tool_name=None),
    ]
    total, by_name = count_tool_calls(items)
    assert total == 3
    assert by_name == {"read_file": 2, "search_code": 1}


def test_count_tool_calls_empty() -> None:
    total, by_name = count_tool_calls([])
    assert total == 0
    assert by_name == {}
