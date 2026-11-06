from pathlib import Path

import pytest

from investigator import repo

SHOP = Path(__file__).resolve().parents[1] / "sample_repos" / "inventory-app"

SHOP_FILES = [
    "README.md",
    "inventory/__init__.py",
    "inventory/orders.py",
    "inventory/pricing.py",
    "inventory/products.py",
    "inventory/stock.py",
]


def test_list_files_returns_sorted_shop_paths() -> None:
    assert repo.list_files(SHOP) == SHOP_FILES


def test_resolve_in_repo_rejects_path_outside_the_folder() -> None:
    with pytest.raises(repo.RepoAccessError, match="outside the repository"):
        repo.resolve_in_repo(SHOP, "../../README.md")


def test_resolve_in_repo_rejects_ignored_directory() -> None:
    with pytest.raises(repo.RepoAccessError, match="ignored directory"):
        repo.resolve_in_repo(SHOP, "inventory/__pycache__/x.py")


def test_resolve_in_repo_rejects_missing_file() -> None:
    with pytest.raises(repo.RepoAccessError, match="File not found: inventory/order.py"):
        repo.resolve_in_repo(SHOP, "inventory/order.py")


def test_read_file_numbers_lines() -> None:
    text = repo.read_file(SHOP, "inventory/pricing.py")
    assert "BULK_DISCOUNT_THRESHOLD = 20" in text
    assert "BULK_DISCOUNT_RATE = 0.10" in text
    assert " 3|" in text
    assert " 4|" in text


def test_read_file_honors_line_range() -> None:
    text = repo.read_file(SHOP, "inventory/pricing.py", start_line=3, end_line=4)
    assert text == "3| BULK_DISCOUNT_THRESHOLD = 20\n4| BULK_DISCOUNT_RATE = 0.10"


def test_read_file_rejects_undecodable_file(tmp_path: Path) -> None:
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(repo.RepoAccessError, match="not valid UTF-8"):
        repo.read_file(tmp_path, "binary.dat")


def test_search_code_finds_product_in_three_files() -> None:
    text = repo.search_code(SHOP, "Product")
    assert "inventory/products.py:5: class Product:" in text
    assert "inventory/pricing.py:1: from inventory.products import Product" in text
    assert "inventory/orders.py:4: from inventory.products import Product" in text


def test_search_code_empty_query() -> None:
    assert repo.search_code(SHOP, "") == "Query is empty."


def test_search_code_no_matches() -> None:
    assert repo.search_code(SHOP, "no-such-token-xyz") == (
        "No matches for: no-such-token-xyz"
    )


def test_search_code_caps_per_file_and_still_shows_later_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("\n".join(f"x = {i}" for i in range(10)))
    (tmp_path / "b.py").write_text("x = 1\n")
    text = repo.search_code(tmp_path, "x =")
    assert "a.py:5:" in text
    assert "b.py:1:" in text
    assert "more than 5 matches in: a.py" in text


def test_search_code_notes_skipped_unreadable_file(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("hello\n")
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe\x00\x01")
    text = repo.search_code(tmp_path, "hello")
    assert "ok.py:1: hello" in text
    assert "1 file skipped (could not read); result may be incomplete." in text
