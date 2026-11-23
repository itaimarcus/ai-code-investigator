import asyncio
from pathlib import Path

import pytest
from agents import SQLiteSession

from main import (
    APPLIED_NOTE,
    DISCARDED_NOTE,
    approval_note,
    parse_args,
    remember_approval,
)


def test_approval_note_names_apply_and_discard() -> None:
    assert approval_note(True) == APPLIED_NOTE
    assert approval_note(False) == DISCARDED_NOTE


def test_remember_approval_appends_a_developer_message() -> None:
    session = SQLiteSession("test-approval")
    remember_approval(session, applied=False)
    items = asyncio.run(session.get_items())
    assert items == [{"role": "developer", "content": DISCARDED_NOTE}]


def test_parse_args_default_is_the_lead(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path)])
    assert args.single is False


def test_parse_args_single(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path), "--single"])
    assert args.single is True


def test_parse_args_unknown_exits(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args([str(tmp_path), "--nope"])


def test_parse_args_accepts_a_folder(tmp_path: Path) -> None:
    args = parse_args([str(tmp_path)])
    assert args.repo == tmp_path.resolve()


def test_parse_args_without_folder_exits() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_missing_folder_exits(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args([str(tmp_path / "nope")])


def test_parse_args_file_is_not_a_folder(tmp_path: Path) -> None:
    file = tmp_path / "notes.txt"
    file.write_text("not a folder\n")
    with pytest.raises(SystemExit):
        parse_args([str(file)])
