from pathlib import Path

from investigator.report import FileReference, InvestigationReport
from investigator.score_report import load_answer_key, score_report

ANSWER_KEY_PATH = (
    Path(__file__).resolve().parents[1] / "sample_answer_keys" / "inventory-app.json"
)


def _report(*citations: FileReference) -> InvestigationReport:
    return InvestigationReport(summary="Product lives in products.py.", citations=list(citations))


def test_load_answer_key() -> None:
    key = load_answer_key(ANSWER_KEY_PATH)
    assert key.question == (
        "Where is the Product class defined, and which files reference it?"
    )
    assert [check.path for check in key.must_cite] == [
        "inventory/products.py",
        "inventory/pricing.py",
        "inventory/orders.py",
    ]
    assert key.must_cite[0].line == 5
    assert key.must_cite[1].line is None
    assert key.must_cite[2].line is None


def test_score_report() -> None:
    key = load_answer_key(ANSWER_KEY_PATH)
    report = _report(
        FileReference(path="inventory/products.py", start_line=5, end_line=8),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=7),
        FileReference(path="inventory/orders.py", start_line=4, end_line=15),
    )
    result = score_report(report, key)
    assert result.passed
    assert result.failed == []


def test_score_report_missing_orders_py() -> None:
    key = load_answer_key(ANSWER_KEY_PATH)
    report = _report(
        FileReference(path="inventory/products.py", start_line=5, end_line=8),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=1),
    )
    result = score_report(report, key)
    assert not result.passed
    assert result.failed == ["missing citation for inventory/orders.py"]


def test_score_report_products_line_not_covered() -> None:
    key = load_answer_key(ANSWER_KEY_PATH)
    report = _report(
        FileReference(path="inventory/products.py", start_line=1, end_line=2),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=1),
        FileReference(path="inventory/orders.py", start_line=4, end_line=4),
    )
    result = score_report(report, key)
    assert not result.passed
    assert result.failed == ["missing citation for inventory/products.py line 5"]
