from pathlib import Path

from investigator import repo
from investigator.tools import RepoContext, ensure_workspace


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
