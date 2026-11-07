from agents import Agent

from investigator.report import InvestigationReport
from investigator.tools import RepoContext, list_files, read_file, search_code

INSTRUCTIONS = """\
You are a code investigator: an assistant that helps developers understand a software repository.
Use the available tools to look at the repository before answering.
Base your answers only on what the tools show you. If something is unclear, say so once, briefly, instead of hedging in every sentence.
Put the conclusion in summary. Put file path and line range in citations, using only locations the tools showed you.
"""

DEFAULT_TOOLS = [list_files, read_file, search_code]


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
