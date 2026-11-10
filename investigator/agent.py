import json

from agents import Agent, RunResult

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

INVESTIGATOR_INSTRUCTIONS = """\
You are a code investigator: an assistant that helps developers understand a software repository.
Use the available tools to look at the repository before answering.
Base your answers only on what the tools show you. If something is unclear, say so once, briefly, instead of hedging in every sentence.
Put the conclusion in summary. Put file path and line range in citations, using only locations the tools showed you.
Do not edit files.
"""

REPAIRER_INSTRUCTIONS = """\
When the user wants failing tests fixed: call run_tests, then replace_in_file on the working copy, then run_tests again. Repeat until the tests pass or replace_in_file reports that the replace limit was reached. Stop editing once tests pass. Edits apply to a copy; do not claim the original project files were updated.
Put the conclusion in summary. Put file path and line range in citations, using only locations the tools showed you.
"""

LEAD_INSTRUCTIONS = """\
You answer the user. You cannot read or edit the repository yourself.
Call investigate_repository to inspect or explain code.
Call repair_repository to fix failing tests.
If a message needs both jobs, call both.
Base the report only on what those tools return. Put the conclusion in summary. Put file path and line range in citations, using only locations they showed you.
"""

DEFAULT_TOOLS = [list_files, read_file, search_code, run_tests, replace_in_file]
INVESTIGATOR_TOOLS = [list_files, read_file, search_code]
REPAIRER_TOOLS = [read_file, run_tests, replace_in_file]


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


def build_investigator(model: str) -> Agent[RepoContext]:
    return Agent[RepoContext](
        name="Investigator",
        instructions=INVESTIGATOR_INSTRUCTIONS,
        model=model,
        output_type=InvestigationReport,
        tools=INVESTIGATOR_TOOLS,
    )


def build_repairer(model: str) -> Agent[RepoContext]:
    return Agent[RepoContext](
        name="Repairer",
        instructions=REPAIRER_INSTRUCTIONS,
        model=model,
        output_type=InvestigationReport,
        tools=REPAIRER_TOOLS,
    )


async def specialist_report_text(result: RunResult) -> str:
    """Turn the specialist's InvestigationReport object into tool-result text."""
    report = result.final_output
    if isinstance(report, InvestigationReport):
        return json.dumps(report.model_dump(mode="json"))
    return str(report)


def build_lead(model: str) -> Agent[RepoContext]:
    investigator = build_investigator(model)
    repairer = build_repairer(model)
    return Agent[RepoContext](
        name="Lead",
        instructions=LEAD_INSTRUCTIONS,
        model=model,
        output_type=InvestigationReport,
        tools=[
            investigator.as_tool(
                tool_name="investigate_repository",
                tool_description=(
                    "Inspect or explain code in the repository. "
                    "Use this for questions about what the code does, where something "
                    "is defined, or why tests fail, when the user is not asking to change files."
                ),
                custom_output_extractor=specialist_report_text,
            ),
            repairer.as_tool(
                tool_name="repair_repository",
                tool_description=(
                    "Fix failing tests by editing the working copy. "
                    "Use this when the user wants tests to pass or asks for a repair."
                ),
                custom_output_extractor=specialist_report_text,
            ),
        ],
    )
