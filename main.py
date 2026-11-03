import json
import os
import time
from dataclasses import asdict

from agents import Runner
from dotenv import load_dotenv

from investigator.agent import build_agent
from investigator.metrics import collect_metrics

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

    start = time.perf_counter()
    result = Runner.run_sync(agent, QUESTION)
    latency_seconds = time.perf_counter() - start

    print(result.final_output)

    metrics = collect_metrics(result, model, latency_seconds)
    print("\n--- Run metrics ---")
    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
