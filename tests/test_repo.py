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
    "pytest.ini",
    "tests/test_pricing.py",
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


def test_run_tests_returns_failure_text(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_sample.py").write_text("def test_fails():\n    assert False\n")
    text = repo.run_tests(tmp_path)
    assert "assert False" in text


def test_search_code_notes_skipped_unreadable_file(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("hello\n")
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe\x00\x01")
    text = repo.search_code(tmp_path, "hello")
    assert "ok.py:1: hello" in text
    assert "1 file skipped (could not read); result may be incomplete." in text


def _mini_repo(tmp_path: Path) -> Path:
    source = tmp_path / "shop"
    (source / "inventory").mkdir(parents=True)
    (source / "inventory" / "app.py").write_text("x = 1\n")
    (source / "README.md").write_text("shop\n")
    cache = source / "inventory" / "__pycache__"
    cache.mkdir()
    (cache / "app.cpython-312.pyc").write_bytes(b"\x00")
    return source


def test_copy_tree_copies_files_and_skips_ignored_dirs(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    dest = tmp_path / "copy"
    repo.copy_tree(source, dest)
    assert repo.list_files(dest) == ["README.md", "inventory/app.py"]
    assert repo.list_files(dest) == repo.list_files(source)
    assert not (dest / "inventory" / "__pycache__").exists()


def test_replace_in_file_replaces_a_unique_snippet(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\ny = 2\n")
    result = repo.replace_in_file(tmp_path, "app.py", "x = 1", "x = 2")
    assert result == "Replaced one match in app.py."
    assert (tmp_path / "app.py").read_text() == "x = 2\ny = 2\n"


def test_replace_in_file_rejects_empty_old_text(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n")
    with pytest.raises(repo.RepoAccessError, match="old_text is empty"):
        repo.replace_in_file(tmp_path, "app.py", "", "x = 2")
    assert (tmp_path / "app.py").read_text() == "x = 1\n"


def test_replace_in_file_rejects_zero_matches(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n")
    with pytest.raises(repo.RepoAccessError, match="No match for old_text"):
        repo.replace_in_file(tmp_path, "app.py", "x = 99", "x = 2")
    assert (tmp_path / "app.py").read_text() == "x = 1\n"


def test_replace_in_file_rejects_multiple_matches(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\nx = 1\n")
    with pytest.raises(repo.RepoAccessError, match="matched 2 times"):
        repo.replace_in_file(tmp_path, "app.py", "x = 1", "x = 2")
    assert (tmp_path / "app.py").read_text() == "x = 1\nx = 1\n"


def test_replace_in_file_rejects_path_outside_the_folder(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\n")
    with pytest.raises(repo.RepoAccessError, match="outside the repository"):
        repo.replace_in_file(tmp_path, "../app.py", "x = 1", "x = 2")


def test_unified_diff_shows_the_changed_line(tmp_path: Path) -> None:
    source = tmp_path / "source"
    work = tmp_path / "work"
    source.mkdir()
    work.mkdir()
    (source / "app.py").write_text("x = 1\n")
    (work / "app.py").write_text("x = 2\n")
    text = repo.unified_diff(source, work, "app.py")
    assert "-x = 1" in text
    assert "+x = 2" in text


def test_copy_file_from_workspace_overwrites_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    work = tmp_path / "work"
    source.mkdir()
    work.mkdir()
    (source / "app.py").write_text("x = 1\n")
    (work / "app.py").write_text("x = 2\n")
    repo.copy_file_from_workspace(source, work, "app.py")
    assert (source / "app.py").read_text() == "x = 2\n"


def test_delete_tree_removes_the_folder(tmp_path: Path) -> None:
    folder = tmp_path / "copy"
    folder.mkdir()
    (folder / "a.txt").write_text("x\n")
    repo.delete_tree(folder)
    assert not folder.exists()


def test_copy_tree_does_not_modify_source(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    dest = tmp_path / "copy"
    repo.copy_tree(source, dest)
    (dest / "only_in_copy.txt").write_text("new\n")
    assert "only_in_copy.txt" not in repo.list_files(source)
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
