import pytest
from pydantic import ValidationError

from investigator.report import FileReference, InvestigationReport


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
