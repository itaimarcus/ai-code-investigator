import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from agents import Runner
from dotenv import load_dotenv

from investigator.agent import build_agent
from investigator.metrics import collect_metrics
from investigator.score_report import load_answer_keys, score_report
from investigator.tools import (
    RepoContext,
    finish_workspace,
    proposed_changes_text,
)

REPO_ROOT = Path(__file__).parent / "sample_repos" / "inventory-app"
ANSWER_KEY = Path(__file__).parent / "sample_answer_keys" / "inventory-app.json"
QUESTION = (
    "The tests are failing. Find the cause, fix it on the working copy "
    "using replace_in_file, and re-run tests until they pass. Then "
    "summarize what you changed and where."
)


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


def review_workspace(context: RepoContext) -> None:
    if not context.has_copy():
        return
    print()
    print(proposed_changes_text(context))
    apply = False
    if context.replaced_paths:
        apply = ask_apply()
        if apply:
            print("Applied changes to the original project.")
        else:
            print("Discarded the working copy. Original project unchanged.")
    else:
        print("Discarded the working copy. Original project unchanged.")
    finish_workspace(context, apply)


def main() -> None:
    load_dotenv()

    require_env("OPENAI_API_KEY")
    model = require_env("OPENAI_MODEL")

    agent = build_agent(model)
    context = RepoContext(source_root=REPO_ROOT, workspace_root=REPO_ROOT)

    start = time.perf_counter()
    result = Runner.run_sync(agent, QUESTION, context=context)
    latency_seconds = time.perf_counter() - start

    print(json.dumps(result.final_output.model_dump(mode="json"), indent=2))

    metrics = collect_metrics(result, model, latency_seconds)
    print("\n--- Run metrics ---")
    print(json.dumps(asdict(metrics), indent=2))

    review_workspace(context)

    keys = load_answer_keys(ANSWER_KEY)
    key = next((item for item in keys if item.question == QUESTION), None)
    if key is None:
        return
    score = score_report(result.final_output, key)
    print("\n--- Score ---")
    print(json.dumps(asdict(score), indent=2))


if __name__ == "__main__":
    main()
