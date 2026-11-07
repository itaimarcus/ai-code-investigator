from dataclasses import dataclass
from pathlib import Path

from agents import RunContextWrapper, function_tool

from investigator import repo


@dataclass
class RepoContext:
    root: Path


@function_tool
def list_files(ctx: RunContextWrapper[RepoContext]) -> str:
    """List all files in the repository, as paths relative to the repository root."""
    return "\n".join(repo.list_files(ctx.context.root))


@function_tool
def read_file(
    ctx: RunContextWrapper[RepoContext],
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read a file from the repository.

    Paths are relative to the repository root, for example inventory/orders.py.
    Optional start_line and end_line are 1-based and inclusive; omit them to read
    from the start or through the end of the file.
    """
    try:
        return repo.read_file(ctx.context.root, path, start_line, end_line)
    except repo.RepoAccessError as exc:
        return str(exc)


@function_tool
def search_code(ctx: RunContextWrapper[RepoContext], query: str) -> str:
    """Search repository files for a literal (exact substring), case-sensitive.

    Returns matching lines as path:line: text.
    """
    return repo.search_code(ctx.context.root, query)


@function_tool
def run_tests(ctx: RunContextWrapper[RepoContext]) -> str:
    """Run the repository's pytest suite and return the printed output.

    Use this when tests are failing or when you need to see whether tests pass.
    There is no path argument; tests always run in the repository root.
    """
    return repo.run_tests(ctx.context.root)
