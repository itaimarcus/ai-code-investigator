from agents import Agent

from investigator.report import InvestigationReport
from investigator.tools import (
    RepoContext,
    list_files,
    read_file,
    replace_in_file,
    run_tests,
    search_code,
)

INSTRUCTIONS = """\
You are a code investigator: an assistant that helps developers understand a software repository.
Use the available tools to look at the repository before answering.
Base your answers only on what the tools show you. If something is unclear, say so once, briefly, instead of hedging in every sentence.
Put the conclusion in summary. Put file path and line range in citations, using only locations the tools showed you.
When the user wants failing tests fixed: call run_tests, then replace_in_file on the working copy, then run_tests again. Repeat until the tests pass or replace_in_file reports that the replace limit was reached. Stop editing once tests pass. Edits apply to a copy; do not claim the original project files were updated.
"""

DEFAULT_TOOLS = [list_files, read_file, search_code, run_tests, replace_in_file]


def build_agent(
    model: str,
    *,
    tools: list | None = None,
    instructions: str | None = None,
) -> Agent[RepoContext]:
    return Agent[RepoContext](
        name="Code Investigator",
        instructions=INSTRUCTIONS if instructions is None else instructions,
        model=model,
        output_type=InvestigationReport,
        tools=DEFAULT_TOOLS if tools is None else tools,
    )
