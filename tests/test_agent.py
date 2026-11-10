import asyncio
import json
from types import SimpleNamespace

from investigator.agent import (
    build_agent,
    build_investigator,
    build_lead,
    build_repairer,
    specialist_report_text,
)
from investigator.report import (
    FileReference,
    InvestigationReport,
    RepairReport,
    RunCounts,
)
from main import choose_agent

MODEL = "test-model"


def _tool_names(agent) -> list[str]:
    return [tool.name for tool in agent.tools]


def test_specialist_report_text_is_json() -> None:
    report = InvestigationReport(
        summary="Product is defined in products.py.",
        citations=[
            FileReference(
                path="inventory/products.py",
                start_line=4,
                end_line=8,
            )
        ],
    )
    text = asyncio.run(specialist_report_text(SimpleNamespace(final_output=report)))
    payload = json.loads(text)
    assert payload == {
        "summary": "Product is defined in products.py.",
        "citations": [
            {
                "path": "inventory/products.py",
                "start_line": 4,
                "end_line": 8,
            }
        ],
    }


def test_specialist_report_text_dumps_repair_report() -> None:
    report = RepairReport(
        summary="Fixed the threshold.",
        files_changed=["inventory/pricing.py"],
        tests_before=RunCounts(passed=2, total=4),
        tests_after=RunCounts(passed=4, total=4),
        tests_failed_names=["test_bulk_discount_at_threshold"],
        success=True,
    )
    text = asyncio.run(specialist_report_text(SimpleNamespace(final_output=report)))
    payload = json.loads(text)
    assert payload["files_changed"] == ["inventory/pricing.py"]
    assert payload["tests_failed_names"] == ["test_bulk_discount_at_threshold"]
    assert payload["tests_before"] == {"passed": 2, "total": 4}
    assert payload["tests_after"] == {"passed": 4, "total": 4}
    assert payload["success"] is True


def test_specialist_report_text_falls_back_to_str() -> None:
    text = asyncio.run(
        specialist_report_text(SimpleNamespace(final_output="plain text"))
    )
    assert text == "plain text"


def test_investigator_tools_are_read_only() -> None:
    assert _tool_names(build_investigator(MODEL)) == [
        "list_files",
        "read_file",
        "search_code",
    ]


def test_repairer_tools() -> None:
    repairer = build_repairer(MODEL)
    assert _tool_names(repairer) == [
        "read_file",
        "run_tests",
        "replace_in_file",
    ]
    assert repairer.output_type is RepairReport


def test_lead_and_single_have_no_output_type() -> None:
    assert build_lead(MODEL).output_type is None
    assert build_agent(MODEL).output_type is None
    assert build_investigator(MODEL).output_type is InvestigationReport


def test_lead_tools_are_the_two_specialists() -> None:
    assert _tool_names(build_lead(MODEL)) == [
        "investigate_repository",
        "repair_repository",
    ]


def test_single_agent_has_five_repo_tools() -> None:
    agent = choose_agent(MODEL, single=True)
    assert agent.name == "Code Investigator"
    assert _tool_names(agent) == _tool_names(build_agent(MODEL))
    assert _tool_names(agent) == [
        "list_files",
        "read_file",
        "search_code",
        "run_tests",
        "replace_in_file",
    ]


def test_default_agent_is_the_lead() -> None:
    agent = choose_agent(MODEL, single=False)
    assert agent.name == "Lead"
    assert _tool_names(agent) == [
        "investigate_repository",
        "repair_repository",
    ]
