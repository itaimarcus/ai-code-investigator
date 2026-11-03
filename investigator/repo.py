from pathlib import Path

IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".pytest_cache"}


def list_files(root: Path) -> list[str]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not IGNORED_DIRS.intersection(relative.parts):
            files.append(relative.as_posix())
    return sorted(files)
