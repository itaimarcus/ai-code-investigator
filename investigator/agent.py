from agents import Agent

from investigator.tools import RepoContext, list_files, read_file, search_code

INSTRUCTIONS = """\
You are a code investigator: an assistant that helps developers understand a software repository.
Use the available tools to look at the repository before answering.
Base your answers only on what the tools show you. If something is unclear, say so once, briefly, instead of hedging in every sentence.
"""


def build_agent(model: str) -> Agent[RepoContext]:
    return Agent[RepoContext](
        name="Code Investigator",
        instructions=INSTRUCTIONS,
        model=model,
        tools=[list_files, read_file, search_code],
    )
