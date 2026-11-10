import pytest
from pydantic import ValidationError

from investigator.report import (
    FileReference,
    InvestigationReport,
    RepairReport,
    RunCounts,
)


def test_file_reference_accepts_valid_range() -> None:
    ref = FileReference(path="inventory/products.py", start_line=5, end_line=8)
    assert ref.path == "inventory/products.py"
    assert ref.start_line == 5
    assert ref.end_line == 8


def test_file_reference_rejects_start_line_zero() -> None:
    with pytest.raises(ValidationError):
        FileReference(path="x.py", start_line=0, end_line=1)


def test_file_reference_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        FileReference(path="x.py", start_line=5, end_line=3)


def test_investigation_report_allows_empty_citations() -> None:
    report = InvestigationReport(summary="Nothing found.", citations=[])
    assert report.citations == []


def test_run_counts_rejects_passed_above_total() -> None:
    with pytest.raises(ValidationError):
        RunCounts(passed=3, total=2)


def test_repair_report_success_follows_full_pass() -> None:
    report = RepairReport(
        summary="Fixed the threshold.",
        files_changed=["inventory/pricing.py"],
        tests_before=RunCounts(passed=2, total=4),
        tests_after=RunCounts(passed=4, total=4),
        tests_failed_names=[
            "test_bulk_discount_at_threshold",
            "test_place_order_applies_bulk_discount_at_threshold",
        ],
        success=False,
    )
    assert report.success is True


def test_repair_report_success_false_when_tests_still_fail() -> None:
    report = RepairReport(
        summary="Still failing.",
        files_changed=[],
        tests_before=RunCounts(passed=2, total=4),
        tests_after=RunCounts(passed=2, total=4),
        tests_failed_names=["test_bulk_discount_at_threshold"],
        success=True,
    )
    assert report.success is False


def test_repair_report_success_false_when_no_tests_ran() -> None:
    report = RepairReport(
        summary="Did not run tests.",
        files_changed=[],
        tests_before=RunCounts(passed=0, total=0),
        tests_after=RunCounts(passed=0, total=0),
        tests_failed_names=[],
        success=True,
    )
    assert report.success is False
