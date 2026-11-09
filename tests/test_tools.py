from pathlib import Path

from investigator import repo
from investigator.tools import (
    MAX_REPLACE_ATTEMPTS,
    RepoContext,
    apply_replace,
    ensure_workspace,
    finish_workspace,
    proposed_changes_text,
)


def _mini_repo(tmp_path: Path) -> Path:
    source = tmp_path / "shop"
    (source / "inventory").mkdir(parents=True)
    (source / "inventory" / "app.py").write_text("x = 1\n")
    (source / "README.md").write_text("shop\n")
    return source


def _context(source: Path, tmp_path: Path) -> RepoContext:
    return RepoContext(
        source_root=source,
        workspace_root=source,
        workspaces_parent=tmp_path / "workspaces",
    )


def test_workspace_root_starts_as_source(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    assert context.workspace_root == source
    assert context.source_root == source
    assert not context.has_copy()


def test_ensure_workspace_points_workspace_root_at_the_copy(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    parent = tmp_path / "workspaces"
    context = RepoContext(
        source_root=source, workspace_root=source, workspaces_parent=parent
    )
    dest = ensure_workspace(context)
    assert context.workspace_root == dest
    assert context.source_root == source
    assert context.has_copy()
    assert dest.parent == parent
    assert repo.list_files(context.workspace_root) == repo.list_files(source)


def test_ensure_workspace_does_not_modify_source(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    ensure_workspace(context)
    (context.workspace_root / "new.txt").write_text("edit\n")
    assert not (source / "new.txt").exists()
    assert "new.txt" not in repo.list_files(source)


def test_ensure_workspace_second_call_reuses_the_copy(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    parent = tmp_path / "workspaces"
    context = RepoContext(
        source_root=source, workspace_root=source, workspaces_parent=parent
    )
    first = ensure_workspace(context)
    second = ensure_workspace(context)
    assert first == second
    assert list(parent.iterdir()) == [first]


def test_apply_replace_copies_then_edits_only_the_workspace(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    message = apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    assert message == "Replaced one match in inventory/app.py."
    assert context.has_copy()
    assert context.replaced_paths == {"inventory/app.py"}
    assert (context.workspace_root / "inventory" / "app.py").read_text() == "x = 2\n"
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"


def test_apply_replace_second_edit_reuses_the_copy(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    parent = tmp_path / "workspaces"
    context = _context(source, tmp_path)
    apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    first_copy = context.workspace_root
    apply_replace(context, "inventory/app.py", "x = 2", "x = 3")
    assert context.workspace_root == first_copy
    assert list(parent.iterdir()) == [first_copy]
    assert (first_copy / "inventory" / "app.py").read_text() == "x = 3\n"
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
    assert context.replaced_paths == {"inventory/app.py"}


def test_apply_replace_returns_error_string_without_changing_files(
    tmp_path: Path,
) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    message = apply_replace(context, "inventory/app.py", "x = 99", "x = 2")
    assert "No match for old_text" in message
    assert context.replaced_paths == set()
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
    assert (context.workspace_root / "inventory" / "app.py").read_text() == "x = 1\n"


def test_ninth_replace_is_refused_and_does_not_write(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    for _ in range(MAX_REPLACE_ATTEMPTS):
        message = apply_replace(context, "inventory/app.py", "missing", "x")
        assert "No match for old_text" in message
    ninth = apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    assert "Replace limit reached (8)" in ninth
    assert context.replace_attempts == MAX_REPLACE_ATTEMPTS
    assert context.replaced_paths == set()
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
    assert (context.workspace_root / "inventory" / "app.py").read_text() == "x = 1\n"


def test_finish_workspace_apply_copies_then_deletes_the_copy(
    tmp_path: Path,
) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    copy = context.workspace_root
    finish_workspace(context, apply=True)
    assert (source / "inventory" / "app.py").read_text() == "x = 2\n"
    assert not copy.exists()
    assert not context.has_copy()


def test_finish_workspace_discard_deletes_copy_and_leaves_source(
    tmp_path: Path,
) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    copy = context.workspace_root
    finish_workspace(context, apply=False)
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
    assert not copy.exists()
    assert not context.has_copy()


def test_failed_replace_copy_is_discarded_without_touching_source(
    tmp_path: Path,
) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    apply_replace(context, "inventory/app.py", "missing", "x")
    assert context.has_copy()
    assert context.replaced_paths == set()
    copy = context.workspace_root
    finish_workspace(context, apply=True)
    assert (source / "inventory" / "app.py").read_text() == "x = 1\n"
    assert not copy.exists()


def test_proposed_changes_text_includes_diff(tmp_path: Path) -> None:
    source = _mini_repo(tmp_path)
    context = _context(source, tmp_path)
    apply_replace(context, "inventory/app.py", "x = 1", "x = 2")
    text = proposed_changes_text(context)
    assert "inventory/app.py" in text
    assert "-x = 1" in text
    assert "+x = 2" in text
