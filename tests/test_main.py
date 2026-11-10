import asyncio

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


def test_parse_args_default_is_the_lead() -> None:
    args = parse_args([])
    assert args.single is False


def test_parse_args_single() -> None:
    args = parse_args(["--single"])
    assert args.single is True


def test_parse_args_unknown_exits() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--nope"])
