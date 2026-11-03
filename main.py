import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from agents import Runner
from dotenv import load_dotenv

from investigator.agent import build_agent
from investigator.metrics import collect_metrics
from investigator.tools import RepoContext

REPO_ROOT = Path(__file__).parent / "sample_repos" / "inventory-app"
QUESTION = "What discount do bulk orders get, and where is it applied?"


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
    result = Runner.run_sync(agent, QUESTION, context=RepoContext(root=REPO_ROOT))
    latency_seconds = time.perf_counter() - start

    print(result.final_output)

    metrics = collect_metrics(result, model, latency_seconds)
    print("\n--- Run metrics ---")
    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
