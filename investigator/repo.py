import difflib
import shutil
import subprocess
import sys
from pathlib import Path

IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".pytest_cache"}
MAX_READ_LINES = 400
MAX_MATCHES_PER_FILE = 5
MAX_MATCHES_TOTAL = 50
MAX_TEST_OUTPUT = 8000
TEST_TIMEOUT_SECONDS = 30


class RepoAccessError(Exception):
    """The requested path is outside the repository, missing, ignored, or not a file."""


def _is_ignored(relative: Path) -> bool:
    return bool(IGNORED_DIRS.intersection(relative.parts))


def list_files(root: Path) -> list[str]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not _is_ignored(relative):
            files.append(relative.as_posix())
    return sorted(files)


def copy_tree(source: Path, dest: Path) -> None:
    """Copy one repository tree. Skip the same ignored directory names as list_files."""
    shutil.copytree(source, dest, ignore=_copy_ignore)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_DIRS}


def resolve_in_repo(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    requested = (root / relative_path).resolve()
    if not requested.is_relative_to(root):
        raise RepoAccessError(f"Path is outside the repository: {relative_path}")
    if _is_ignored(Path(relative_path)) or _is_ignored(requested.relative_to(root)):
        raise RepoAccessError(f"Path is in an ignored directory: {relative_path}")
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
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise RepoAccessError(f"File is not valid UTF-8 text: {relative_path}") from exc
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


def replace_in_file(
    root: Path, relative_path: str, old_text: str, new_text: str
) -> str:
    if not old_text:
        raise RepoAccessError("old_text is empty.")
    path = resolve_in_repo(root, relative_path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RepoAccessError(
            f"File is not valid UTF-8 text: {relative_path}"
        ) from exc
    matches = content.count(old_text)
    if matches == 0:
        raise RepoAccessError(
            f"No match for old_text in {relative_path}. "
            "Read the file and send the exact snippet to replace."
        )
    if matches > 1:
        raise RepoAccessError(
            f"old_text matched {matches} times in {relative_path}. "
            "Send a longer snippet that appears exactly once."
        )
    path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Replaced one match in {relative_path}."


def unified_diff(
    source_root: Path, workspace_root: Path, relative_path: str
) -> str:
    original = resolve_in_repo(source_root, relative_path)
    edited = resolve_in_repo(workspace_root, relative_path)
    old_lines = original.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = edited.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )


def copy_file_from_workspace(
    source_root: Path, workspace_root: Path, relative_path: str
) -> None:
    edited = resolve_in_repo(workspace_root, relative_path)
    original = resolve_in_repo(source_root, relative_path)
    shutil.copy2(edited, original)


def delete_tree(path: Path) -> None:
    shutil.rmtree(path)


def search_code(root: Path, query: str) -> str:
    if not query:
        return "Query is empty."

    matches: list[str] = []
    truncated_files: list[str] = []
    skipped = 0
    hit_total_cap = False

    for relative_path in list_files(root):
        if len(matches) >= MAX_MATCHES_TOTAL:
            hit_total_cap = True
            break
        try:
            path = resolve_in_repo(root, relative_path)
            lines = path.read_text(encoding="utf-8").splitlines()
        except (RepoAccessError, UnicodeDecodeError, OSError):
            skipped += 1
            continue

        file_hits = 0
        for line_number, line in enumerate(lines, start=1):
            if query not in line:
                continue
            if file_hits >= MAX_MATCHES_PER_FILE:
                truncated_files.append(relative_path)
                break
            if len(matches) >= MAX_MATCHES_TOTAL:
                hit_total_cap = True
                break
            matches.append(f"{relative_path}:{line_number}: {line}")
            file_hits += 1
        if hit_total_cap:
            break

    if not matches:
        text = f"No matches for: {query}"
    else:
        text = "\n".join(matches)

    notes: list[str] = []
    if hit_total_cap:
        notes.append(
            f"stopped after {MAX_MATCHES_TOTAL} matches (sorted path order); "
            "later files may be missing."
        )
    if truncated_files:
        listed = ", ".join(truncated_files)
        notes.append(f"more than {MAX_MATCHES_PER_FILE} matches in: {listed}")
    if skipped:
        noun = "file" if skipped == 1 else "files"
        notes.append(
            f"{skipped} {noun} skipped (could not read); result may be incomplete."
        )
    if notes:
        text += "\n\n" + "\n".join(f"[{note}]" for note in notes)
    return text


def run_tests(root: Path) -> str:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        partial = _combine_stdio(exc.stdout, exc.stderr)
        return _clip_test_output(
            f"{partial}\n[pytest timed out after {TEST_TIMEOUT_SECONDS} seconds]"
        )
    except OSError as exc:
        return f"Could not start pytest: {exc}"

    text = _combine_stdio(completed.stdout, completed.stderr)
    if not text.strip():
        text = f"pytest produced no output (exit code {completed.returncode})."
    return _clip_test_output(text)


def _combine_stdio(stdout: str | bytes | None, stderr: str | bytes | None) -> str:
    return _as_text(stdout) + _as_text(stderr)


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _clip_test_output(text: str) -> str:
    if len(text) <= MAX_TEST_OUTPUT:
        return text
    kept = text[-MAX_TEST_OUTPUT:]
    return (
        f"[output truncated; showing last {MAX_TEST_OUTPUT} characters]\n{kept}"
    )
