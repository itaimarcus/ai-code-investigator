from pathlib import Path

IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".pytest_cache"}
MAX_READ_LINES = 400


class RepoAccessError(Exception):
    """The requested path is outside the repository, missing, or not a file."""


def list_files(root: Path) -> list[str]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not IGNORED_DIRS.intersection(relative.parts):
            files.append(relative.as_posix())
    return sorted(files)


def resolve_in_repo(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    requested = (root / relative_path).resolve()
    if not requested.is_relative_to(root):
        raise RepoAccessError(f"Path is outside the repository: {relative_path}")
    if not requested.exists():
        raise RepoAccessError(
            f"File not found: {relative_path}. Use list_files to see available files."
        )
    if not requested.is_file():
        raise RepoAccessError(f"Not a file: {relative_path}")
    return requested


def read_file(
    root: Path,
    relative_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    path = resolve_in_repo(root, relative_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)

    start = 1 if start_line is None else start_line
    end = total if end_line is None else end_line
    if start < 1 or end < start:
        raise RepoAccessError(
            f"Invalid line range: start_line={start}, end_line={end} "
            f"(file has {total} lines)"
        )

    selected = lines[start - 1 : end]
    stopped_early = len(selected) > MAX_READ_LINES
    if stopped_early:
        selected = selected[:MAX_READ_LINES]

    last_printed = start + len(selected) - 1 if selected else start
    width = len(str(last_printed))
    numbered = [
        f"{number:>{width}}| {line}"
        for number, line in enumerate(selected, start=start)
    ]
    text = "\n".join(numbered)
    if stopped_early:
        text += (
            f"\n\n[stopped at line {last_printed}; {total} lines in file. "
            "Request another range to continue.]"
        )
    return text
