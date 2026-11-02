from agents import Agent

INSTRUCTIONS = """\
You are a code investigator: an assistant that helps developers understand software projects.
Answer clearly and concisely. If you are not sure about something, say so instead of guessing.
"""


def build_agent(model: str) -> Agent:
    return Agent(
        name="Code Investigator",
        instructions=INSTRUCTIONS,
        model=model,
    )
