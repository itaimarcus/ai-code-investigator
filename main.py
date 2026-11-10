import asyncio
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from agents import Runner, SQLiteSession
from dotenv import load_dotenv

from investigator.agent import build_agent
from investigator.metrics import collect_metrics
from investigator.score_report import AnswerKey, load_answer_keys, score_report
from investigator.tools import (
    RepoContext,
    finish_workspace,
    proposed_changes_text,
    start_run,
)

REPO_ROOT = Path(__file__).parent / "sample_repos" / "inventory-app"
ANSWER_KEY = Path(__file__).parent / "sample_answer_keys" / "inventory-app.json"
QUESTION = (
    "What does this repository implement? "
    "Name the main types and functions, and cite the file and lines where each is defined."
)
APPLIED_NOTE = "Applied these changes to the original project."
DISCARDED_NOTE = "Discarded the working copy. The original project is unchanged."


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing; set it in .env")
    return value


def ask_apply() -> bool:
    while True:
        answer = input(
            "Apply these changes to the original project? y/n\n"
        ).strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("Type y or n.")


def approval_note(applied: bool) -> str:
    if applied:
        return APPLIED_NOTE
    return DISCARDED_NOTE


def remember_approval(session: SQLiteSession, applied: bool) -> None:
    """Append the y/n decision to the transcript, after this turn's report.

    input() only returns a string to Python. The model sees it on the next
    turn because this writes that string into the session.
    """
    asyncio.run(
        session.add_items(
            [{"role": "developer", "content": approval_note(applied)}]
        )
    )


def review_workspace(context: RepoContext, session: SQLiteSession) -> None:
    if not context.has_copy():
        return
    print()
    print(proposed_changes_text(context))
    asked = bool(context.replaced_paths)
    apply = ask_apply() if asked else False
    if not asked:
        print(DISCARDED_NOTE)
    finish_workspace(context, apply)
    if asked:
        print(approval_note(apply))
        remember_approval(session, apply)


def read_next_message() -> str | None:
    while True:
        message = input("> ").strip()
        if message.lower() in {"q", "quit"}:
            return None
        if message:
            return message
        print("Type a question, or q to quit.")


def run_turn(
    agent,
    context: RepoContext,
    session: SQLiteSession,
    message: str,
    model: str,
    keys: list[AnswerKey],
) -> None:
    start_run(context)
    start = time.perf_counter()
    result = Runner.run_sync(agent, message, context=context, session=session)
    latency_seconds = time.perf_counter() - start

    print(json.dumps(result.final_output.model_dump(mode="json"), indent=2))

    metrics = collect_metrics(result, model, latency_seconds)
    print("\n--- Run metrics ---")
    print(json.dumps(asdict(metrics), indent=2))

    review_workspace(context, session)

    key = next((item for item in keys if item.question == message), None)
    if key is None:
        return
    score = score_report(result.final_output, key)
    print("\n--- Score ---")
    print(json.dumps(asdict(score), indent=2))


def main() -> None:
    load_dotenv()

    require_env("OPENAI_API_KEY")
    model = require_env("OPENAI_MODEL")

    agent = build_agent(model)
    context = RepoContext(source_root=REPO_ROOT, workspace_root=REPO_ROOT)
    session = SQLiteSession("inventory-app")
    keys = load_answer_keys(ANSWER_KEY)

    message: str | None = QUESTION
    while message is not None:
        run_turn(agent, context, session, message, model, keys)
        message = read_next_message()


if __name__ == "__main__":
    main()
