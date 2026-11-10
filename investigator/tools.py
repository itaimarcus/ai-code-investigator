import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agents import RunContextWrapper, function_tool

from investigator import repo

DEFAULT_WORKSPACES_PARENT = Path(__file__).resolve().parent.parent / "workspaces"
MAX_REPLACE_ATTEMPTS = 8


@dataclass
class RepoContext:
    source_root: Path
    workspace_root: Path
    workspaces_parent: Path | None = None
    replace_attempts: int = 0
    replaced_paths: set[str] = field(default_factory=set)

    def has_copy(self) -> bool:
        return self.workspace_root.resolve() != self.source_root.resolve()


def ensure_workspace(context: RepoContext) -> Path:
    """Create a full copy of source_root under workspaces/<id>/ if none exists yet.

    Not a tool. replace_in_file calls this. A second call returns the same path.
    """
    if context.has_copy():
        return context.workspace_root
    parent = context.workspaces_parent
    if parent is None:
        parent = DEFAULT_WORKSPACES_PARENT
    parent.mkdir(parents=True, exist_ok=True)
    dest = parent / uuid.uuid4().hex
    repo.copy_tree(context.source_root, dest)
    context.workspace_root = dest
    return dest


@function_tool
def list_files(ctx: RunContextWrapper[RepoContext]) -> str:
    """List all files in the repository, as paths relative to the repository root."""
    return "\n".join(repo.list_files(ctx.context.workspace_root))


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
        return repo.read_file(ctx.context.workspace_root, path, start_line, end_line)
    except repo.RepoAccessError as exc:
        return str(exc)


@function_tool
def search_code(ctx: RunContextWrapper[RepoContext], query: str) -> str:
    """Search repository files for a literal (exact substring), case-sensitive.

    Returns matching lines as path:line: text.
    """
    return repo.search_code(ctx.context.workspace_root, query)


def apply_replace(
    context: RepoContext, path: str, old_text: str, new_text: str
) -> str:
    """Copy to a workspace if needed, then replace one unique snippet on that copy."""
    if context.replace_attempts >= MAX_REPLACE_ATTEMPTS:
        return (
            f"Replace limit reached ({MAX_REPLACE_ATTEMPTS}) for this run. "
            "Do not edit further; report what you tried."
        )
    context.replace_attempts += 1
    ensure_workspace(context)
    try:
        result = repo.replace_in_file(
            context.workspace_root, path, old_text, new_text
        )
    except repo.RepoAccessError as exc:
        return str(exc)
    context.replaced_paths.add(Path(path).as_posix())
    return result


def proposed_changes_text(context: RepoContext) -> str:
    if not context.replaced_paths:
        return "No successful file changes."
    blocks = ["--- Proposed changes (copy vs original) ---"]
    for relative_path in sorted(context.replaced_paths):
        blocks.append(
            repo.unified_diff(
                context.source_root, context.workspace_root, relative_path
            )
        )
    return "\n".join(blocks)


def start_run(context: RepoContext) -> None:
    """Zero replace bookkeeping so the cap of 8 applies to this run only.

    Not a tool. main.py calls this before each Runner.run_sync.
    Does not delete a workspace copy. finish_workspace does that after the run,
    and the diff is printed from replaced_paths before that delete.
    """
    context.replace_attempts = 0
    context.replaced_paths = set()


def finish_workspace(context: RepoContext, apply: bool) -> None:
    if not context.has_copy():
        return
    if apply:
        for relative_path in sorted(context.replaced_paths):
            repo.copy_file_from_workspace(
                context.source_root, context.workspace_root, relative_path
            )
    repo.delete_tree(context.workspace_root)
    context.workspace_root = context.source_root


@function_tool
def replace_in_file(
    ctx: RunContextWrapper[RepoContext],
    path: str,
    old_text: str,
    new_text: str,
) -> str:
    """Replace exactly one occurrence of old_text with new_text in an existing file.

    Paths are relative to the repository root, for example inventory/pricing.py.
    old_text must match the file exactly, including spaces. If it is missing or
    appears more than once, this returns an error; send a longer unique snippet.
    The first call copies the repository to a workspace; later tools in this
    run use that copy. The original folder is not written. Python refuses
    further replaces after 8 calls in this run.
    """
    return apply_replace(ctx.context, path, old_text, new_text)


@function_tool
def run_tests(ctx: RunContextWrapper[RepoContext]) -> str:
    """Run the repository's pytest suite and return the printed output.

    Use this when tests are failing or when you need to see whether tests pass.
    There is no path argument; tests always run in the repository root.
    """
    return repo.run_tests(ctx.context.workspace_root)
