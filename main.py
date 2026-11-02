import os

from agents import Runner
from dotenv import load_dotenv

from investigator.agent import build_agent

QUESTION = "In two or three sentences, what is a Python virtual environment and why is it useful?"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing; set it in .env")
    return value


def main() -> None:
    load_dotenv()

    require_env("OPENAI_API_KEY")
    model = require_env("OPENAI_MODEL")

    agent = build_agent(model)
    result = Runner.run_sync(agent, QUESTION)

    print(result.final_output)


if __name__ == "__main__":
    main()
