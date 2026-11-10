import asyncio

from agents import SQLiteSession

from main import APPLIED_NOTE, DISCARDED_NOTE, approval_note, remember_approval


def test_approval_note_names_apply_and_discard() -> None:
    assert approval_note(True) == APPLIED_NOTE
    assert approval_note(False) == DISCARDED_NOTE


def test_remember_approval_appends_a_developer_message() -> None:
    session = SQLiteSession("test-approval")
    remember_approval(session, applied=False)
    items = asyncio.run(session.get_items())
    assert items == [{"role": "developer", "content": DISCARDED_NOTE}]
