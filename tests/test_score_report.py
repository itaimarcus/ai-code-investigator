from pathlib import Path

from investigator.report import FileReference, InvestigationReport
from investigator.score_report import AnswerKey, load_answer_keys, score_report

ANSWER_KEY_PATH = (
    Path(__file__).resolve().parents[1] / "sample_answer_keys" / "inventory-app.json"
)


def _report(*citations: FileReference) -> InvestigationReport:
    return InvestigationReport(summary="Product lives in products.py.", citations=list(citations))


def _product_key() -> AnswerKey:
    return load_answer_keys(ANSWER_KEY_PATH)[0]


def _bulk_key() -> AnswerKey:
    return load_answer_keys(ANSWER_KEY_PATH)[1]


def test_load_answer_keys() -> None:
    keys = load_answer_keys(ANSWER_KEY_PATH)
    assert len(keys) == 2

    product = keys[0]
    assert product.question == (
        "Where is the Product class defined, and which files reference it?"
    )
    assert [check.path for check in product.must_cite] == [
        "inventory/products.py",
        "inventory/pricing.py",
        "inventory/orders.py",
    ]
    assert product.must_cite[0].line == 5
    assert product.must_cite[1].line is None
    assert product.must_cite[2].line is None

    bulk = keys[1]
    assert bulk.question == (
        "What discount do bulk orders get, and where is it applied?"
    )
    assert [check.path for check in bulk.must_cite] == [
        "inventory/pricing.py",
        "inventory/orders.py",
    ]
    assert bulk.must_cite[0].line == 4
    assert bulk.must_cite[1].line is None


def test_score_report() -> None:
    report = _report(
        FileReference(path="inventory/products.py", start_line=5, end_line=8),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=7),
        FileReference(path="inventory/orders.py", start_line=4, end_line=15),
    )
    result = score_report(report, _product_key())
    assert result.passed
    assert result.failed == []


def test_score_report_missing_orders_py() -> None:
    report = _report(
        FileReference(path="inventory/products.py", start_line=5, end_line=8),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=1),
    )
    result = score_report(report, _product_key())
    assert not result.passed
    assert result.failed == ["missing citation for inventory/orders.py"]


def test_score_report_products_line_not_covered() -> None:
    report = _report(
        FileReference(path="inventory/products.py", start_line=1, end_line=2),
        FileReference(path="inventory/pricing.py", start_line=1, end_line=1),
        FileReference(path="inventory/orders.py", start_line=4, end_line=4),
    )
    result = score_report(report, _product_key())
    assert not result.passed
    assert result.failed == ["missing citation for inventory/products.py line 5"]


def test_score_report_bulk_missing_pricing_line() -> None:
    report = _report(
        FileReference(path="inventory/orders.py", start_line=17, end_line=17),
    )
    result = score_report(report, _bulk_key())
    assert not result.passed
    assert result.failed == ["missing citation for inventory/pricing.py line 4"]
