# AI Code Investigator

A Python project, using the **OpenAI Agents SDK**, that investigates software repositories: answers questions about code, and later will debug failing tests, propose fixes, and apply them only after human approval.

Built incrementally. The goal is both a working system and a clear understanding of how agents, tools, and application code fit together.

Private working notes (collaboration rules, prompt drafts, learning backlog) live in `ROADMAP.md`, which is git-ignored. This README is the committed project description.

## Project goals

- Understand agent execution, tool calling, context, and the boundary between model decisions and Python code.
- Design workflows for code exploration, debugging, and repair.
- Evaluate behavior with repeatable examples, not only one-off demos.
- Add technologies (MCP, multi-agent, retrieval, hosted tools) when they serve a real purpose.
- Apply engineering practices progressively; do not add infrastructure before it is needed.

## Intended capabilities (not all built yet)

- Explore Python repositories and answer with file and line references.
- Investigate failing `pytest` tests and report likely causes with evidence.
- Propose edits on a **working copy**, run tests, revise within a bounded number of attempts.
- Require **explicit human approval** before changing the original repository.
- Measure quality, cost, latency, and tool use.
- Support GitHub repos and **Model Context Protocol (MCP)**.

## Getting started

**Requirements:** Python 3.12, an OpenAI API key, internet access for model calls.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `.env` in the project root (git-ignored):

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-6-luna
```

```bash
python main.py
```

`load_dotenv()` loads `.env`. The SDK reads `OPENAI_API_KEY` from the environment; it is never passed to `Agent`. `main.py` reads `OPENAI_MODEL` and passes it to `build_agent(model)`. A missing variable raises `RuntimeError` before any API call.

## How we verify

Three kinds of check. Every time we add behavior, we say which of these we used and what we compared.

1. **Smoke tests (no model, no cost).** A smoke test is a quick check that the main path works. Ours are one-off `python -c` commands, not saved as pytest yet. We do not put a `main` block inside `sample_repos/inventory-app/`, because the agent reads that folder. Commands are listed under each step below.

2. **Agent run + printed metrics.** `python main.py` calls the model. After the answer it prints JSON: `requests` (model HTTP calls, not tool calls), token counts, latency, estimated cost.

3. **OpenAI traces.** Each run is recorded automatically. Open [Traces (Agents SDK)](https://platform.openai.com/logs?api=traces), pick the latest **Agent workflow** by timestamp. Check: number of `POST /v1/responses` equals printed `requests`; tool names and arguments; adding per-turn token counts equals printed `input_tokens` / `output_tokens`; span duration is close to printed `latency_seconds` (ours is slightly larger because it includes SDK setup).

**Cost** is an **estimate**, not a bill. Token counts come from `result.context_wrapper.usage`. Prices come from [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and are stored in `investigator/metrics.py` for `gpt-6-luna` only (USD per 1M tokens: input $0.10, cached input $0.01, 30-minute cache write $0.125, output $0.50). Reasoning tokens are already inside `output_tokens` and use the output price. Unknown models still run and print `estimated_cost_usd: null`.

A **request** is one model HTTP call. A **tool call** is our Python function. One request can include several tool calls. `"requests": 3` with four tool calls is normal.

## Current status

**M0 complete. M1 in progress through step 1.4.** Next: step 1.5 structured Pydantic answers.

The agent investigates `sample_repos/inventory-app/` only. It can list files, read them, and search for a literal, case-sensitive substring. The model does not choose that folder. Paths it names must stay inside it. It cannot edit, and has no pytest tests of our tools.

```text
main.py                       # config, run, print answer + metrics
investigator/agent.py         # name, instructions, model, tools
investigator/tools.py         # RepoContext + @function_tool wrappers
investigator/repo.py          # disk access (list, resolve, read, search); no SDK
investigator/metrics.py       # tokens, latency, cost estimate
sample_repos/inventory-app/   # investigation target
```

Current question in `main.py`: `Where is the Product class defined, and which files reference it?`

## What we built and how we checked it

### M0 — Hello agent

Minimal `Agent` + `Runner.run_sync`, no tools. Metrics printed after each run.

**Checked:** `python main.py` printed an answer; metrics showed `"requests": 1`. Traces: one `POST /v1/responses`; token counts matched. Cost matched a hand calculation from the pricing table (input × $0.10 + output × $0.50, per million tokens). Latency for the same call varied (about 3 s vs 9.5 s) because of provider-side wait, not our code.

### M1.1 — Sample project `inventory-app`

```text
sample_repos/inventory-app/     # folder given to the agent
├── README.md
└── inventory/                  # importable package (name cannot contain '-')
    ├── products.py             # Product: sku, name, unit_price
    ├── stock.py                # Stock + OutOfStockError
    ├── pricing.py              # 10% off from 20 units
    └── orders.py               # place_order: stock then pricing
```

The outer name may use a hyphen; the inner package name may not (`import inventory-src` is invalid). The sample project is committed with this repo.

There is **no written answer key file** yet (decided to add at step 1.6 / M2). We know the facts because we wrote the code. The key must never live inside `inventory-app/` (the agent can read that folder). Sample-project pytest tests wait for M3.

**Checked with a smoke test** from `sample_repos/inventory-app/` (imports work here; `python inventory/orders.py` does not):

```bash
python -c "
from inventory.products import Product
from inventory.stock import Stock, OutOfStockError
from inventory.orders import place_order
p = Product('MUG-01', 'Coffee mug', 5.0)
s = Stock(); s.add('MUG-01', 30)
print('small order:', place_order(s, p, 2).total, '| left:', s.available('MUG-01'))
print('bulk order:', place_order(s, p, 20).total, '| left:', s.available('MUG-01'))
try:
    place_order(s, p, 50)
except OutOfStockError as e:
    print('too many:', e)
"
```

Expected: `10.0` / 28 left; `90.0` / 8 left; `OutOfStockError`.

### M1.2 — `list_files`

A **tool** is a Python function the model may ask us to run. `@function_tool` (Agents SDK; not LangChain `@tool`) builds the schema from the name, types, and docstring. The SDK runs the function and sends the return string back to the model. That repeat is the **agentic loop**.

The folder is `RepoContext(root=...)` passed to `Runner.run_sync`. Tools receive it as `ctx: RunContextWrapper[RepoContext]`; `ctx.context.root` is the folder. The model never sees it (`list_files` schema has no parameters). `ctx` exists only while a tool runs; after the run, the same envelope is `result.context_wrapper`.

`repo.py` talks to the disk; `tools.py` only wraps it for the agent.

**Checked:**

```bash
python -c "from pathlib import Path; from investigator import repo; print(repo.list_files(Path('sample_repos/inventory-app')))"
python -c "from investigator.tools import list_files; print(list_files.name); print(list_files.description); print(list_files.params_json_schema)"
```

Expected: six relative paths; schema `'properties': {}`. An earlier `python main.py` (question about files) listed all six, `"requests": 2`, input tokens 64 → 281. Trace: `list_files` between two model turns; turn tokens summed to the printout.

### M1.3 — `read_file`

The model now names a path. That string is untrusted. `resolve_in_repo` refuses paths outside `sample_repos/inventory-app/` (for example `../../.env`). **Do not test confinement with `.env`.** If the check were buggy, the command would print the secret. Use `../../README.md`.

Missing or illegal paths: `repo.py` raises `RepoAccessError`; `tools.py` returns `str(error)` so the run continues. The model chooses the next tool; `read_file` does not call `list_files` itself.

Output: numbered lines, optional `start_line` / `end_line` (1-based, inclusive), cap 400 lines per call (request another range to continue). Path confinement is not a denylist: `.env` *inside* the allowed folder would still be readable (deferred).

**Checked (no model):**

```bash
python -c "from pathlib import Path; from investigator import repo; print(repo.read_file(Path('sample_repos/inventory-app'), 'inventory/pricing.py'))"
python -c "from pathlib import Path; from investigator import repo; print(repo.read_file(Path('sample_repos/inventory-app'), 'inventory/pricing.py', start_line=3, end_line=4))"
python -c "from pathlib import Path; from investigator import repo; repo.read_file(Path('sample_repos/inventory-app'), '../../README.md')"
python -c "from pathlib import Path; from investigator import repo; repo.read_file(Path('sample_repos/inventory-app'), 'inventory/order.py')"
```

Expected: full numbered `pricing.py` including `BULK_DISCOUNT_THRESHOLD = 20` and `BULK_DISCOUNT_RATE = 0.10`; two-line range; `RepoAccessError` outside the folder; `File not found: inventory/order.py. Use list_files to see available files.` Calling `repo.read_file` from the terminal prints a traceback (nothing catches the exception). The agent sees only the message string.

**Checked (model + trace):** `python main.py` answered 10% off for 20+ units, used by `place_order`. Facts correct; printed text named functions, not `pricing.py` / `orders.py`. Metrics: `"requests": 3`, ~1200 input tokens, ~8.2 s, cost from the pricing table. Trace ([Agents SDK logs](https://platform.openai.com/logs?api=traces)): three `POST /v1/responses`; `list_files` then three `read_file`s in one turn (including `README.md`, not required); final answer with no tools. Latency matched ~8146 ms. Tool spans 1–5 ms. Order inside a batch does not matter: all three reads were requested before any file body was seen.

## Architecture and design decisions

Guiding rule: **the agent reasons and proposes; Python executes and enforces boundaries.**

| Area | Approach | Rationale |
| --- | --- | --- |
| Framework | Python + OpenAI Agents SDK | Learn agents, tools, and lifecycle before another orchestrator. |
| Interface | `main.py`; question and instructions in source | Agent behavior before CLI/UI. |
| Config | `.env` + `python-dotenv` | Secrets and model name stay out of code. |
| Dependencies | `requirements.txt` | Change only if a clear need arises. |
| Internal data | `@dataclass` (`RunMetrics`, `RepoContext`) | No validation needed; Pydantic later for agent `output_type`. |
| Repo scope | Local, trusted Python first | Investigation before untrusted execution or GitHub. |
| Exploration | Custom list/read/search tools | Model pulls files on demand; we control path safety and size. |
| Tool context | SDK `RunContextWrapper` + `RepoContext` | We choose the folder; the model cannot. |
| File access | `repo.py` (disk) / `tools.py` (agent) | One place to harden later; tools stay thin. |
| Editing | Working copy (from M4) | Original files stay unchanged until approval. |
| Approval | Explicit human approval (from M4) | Required, not optional. |
| Orchestration | Compare agent-driven vs Python-driven later | Do not commit the whole project to one style now. |
| Evaluation | Small evals in M2 | Measure prompts, models, tools. |
| Observability | Tokens, estimated cost, latency, traces | Cost uses OpenAI list prices; traces confirm usage. |
| Integrations | MCP, GitHub, multi-agent, hosted tools later | When they enable a capability or a fair experiment. |

**Sync vs async (open):** `Runner.run_sync` now. `await Runner.run` when we need parallel evals, several users, streaming (`Runner.run_streamed`), or parallel agents. Threads are another option (sync code, several waiters). Decide when a need appears.

**Trusted repos vs original files:** trusting the sample code is not a claim that unknown repos are safe. `pytest` would run their code with local permissions. A working copy is not a sandbox.

**Local tools vs uploading a repo:** tools run here. Only the strings they return go to the model.

## Development roadmap

| Milestone | Scope | Definition of Done |
| --- | --- | --- |
| **M0 — Hello Agent** (completed) | Agent, Runner, config, metrics, tracing | `python main.py` prints answer + metrics; trace inspectable |
| **M1 — Repository Q&A** (in progress; 1.4 done) | list, read, search; Pydantic answers; pytest for tools | Questions about the sample project, including multi-file ones, with file references; tool tests pass; metrics include tool calls |
| **M2 — First evaluations** | Known-answer set, scorecard, compare variants | Repeatable scorecard; at least two variants |
| **M3 — Failing-test investigation** | `run_tests` on trusted samples | Find the buggy function in seeded examples |
| **M4 — Repair, retries, approval** | Working copy, bounded retries, diff, approval | Fixes seeded bugs; original unchanged without approval |
| **M5 — SDK patterns** | Guardrails, HITL, sessions | Experiments defined when this starts |
| **M6 — Multi-agent** | Handoffs vs agent-as-tool vs single agent | Compare with the eval suite |
| **M7 — MCP and GitHub** | MCP client and server, GitHub repos | Integration and safety criteria before coding |

**Next implementation step: 1.5 structured Pydantic output** (`output_type`). Then 1.6 tool-call metrics, pytest, Definition of Done.

Deferred until needed: Ruff, GitHub Actions CI, `logging`, CLI/UI, Docker/E2B, prompt-injection defenses, RAG vs text search, LangGraph, secret-file denylist, pinning `requirements.txt`.
