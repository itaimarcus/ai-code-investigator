# AI Code Investigator

A Python project, using the **OpenAI Agents SDK**, that investigates software repositories: answers questions about code, investigates failing tests, and later will propose fixes and apply them only after human approval.

Built incrementally. The goal is both a working system and a clear understanding of how agents, tools, and application code fit together.

Private working notes (prompt drafts, learning backlog) live in `ROADMAP.md`, which is git-ignored. How to work with Itai is in that file, under **How to work with Itai**; `AGENTS.md` points new Cursor agents there. This README is the committed project description.

## Project goals

- Understand agent execution, tool calling, context, and the boundary between model decisions and Python code.
- Design workflows for code exploration, debugging, and repair.
- Evaluate behavior with repeatable examples, not only one-off demos.
- Add technologies (MCP, multi-agent, retrieval, hosted tools) when they serve a real purpose.
- Apply engineering practices progressively; do not add infrastructure before it is needed.

## Intended capabilities (not all built yet)

- Explore Python repositories and answer with file and line references.
- Investigate failing `pytest` tests and report likely causes with evidence. (**M3:** `run_tests` on the sample shop.)
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

Four kinds of check. Every time we add behavior, we say which of these we used and what we compared.

1. **pytest (no OpenAI, no cost).** Saved checks of our Python (`list_files`, `read_file`, `search_code`, `run_tests`, `replace_in_file`, workspace copy, cost math, report fields, `load_answer_keys`, `score_report`). From the project root, with `.venv` active: `pytest`. These tests do not call the language model. They live in `tests/`, outside the folder the agent can read. Shop tests are not collected here.

2. **Shop pytest (no OpenAI).** From `sample_repos/inventory-app/`: `python -m pytest -q`. Expected: 2 passed, 2 failed. The two failures are the planted bulk-discount bug (quantity 20).

3. **Agent run + printed metrics + optional score.** `python main.py` calls the model **once** (whatever `QUESTION` is in that file). After the report it prints JSON: `requests` (model HTTP calls), `tool_calls` (our Python functions, also split by name), token counts, latency, estimated cost. If `QUESTION` matches a row in `sample_answer_keys/inventory-app.json`, it also prints a score (`passed` plus any missing citations). If there is no matching row, it prints report and metrics only. You can still read the report yourself: you know the shop because we wrote it.

4. **OpenAI traces.** Each run is recorded automatically. Open [Traces (Agents SDK)](https://platform.openai.com/logs?api=traces), pick the latest **Agent workflow** by timestamp. Check: number of `POST /v1/responses` equals printed `requests`; number of tool rows equals printed `tool_calls`; tool names and arguments; adding per-turn token counts equals printed `input_tokens` / `output_tokens`; span duration is close to printed `latency_seconds` (ours is slightly larger because it includes SDK setup).

**Cost** is an **estimate**, not a bill. Token counts come from `result.context_wrapper.usage`. Prices come from [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and are stored in `investigator/metrics.py` for `gpt-6-luna` only (USD per 1M tokens: input $0.10, cached input $0.01, 30-minute cache write $0.125, output $0.50). Reasoning tokens are already inside `output_tokens` and use the output price. Unknown models still run and print `estimated_cost_usd: null`.

A **request** is one model HTTP call. A **tool call** is our Python function. One request can include several tool calls. `"requests": 3` with four tool calls is normal.

## Current status

**M0–M3 complete. M4.1–4.3 in progress (4.4 approval not built).** The agent can investigate the sample shop, run its tests, and try a fix on a **copy** (at most **8** `replace_in_file` calls per `python main.py`). The original shop is not written until 4.4.

The printed result is a report with a short summary plus file and line citations. Metrics include how many tools ran, by name. If `QUESTION` matches a row in `sample_answer_keys/inventory-app.json`, a score prints after that. The current question asks for a **fix**; that string is not in the JSON, so no score prints. The model does not choose the shop folder. Paths it names must stay inside it.

`build_agent(model)` uses default tools and instructions. Callers may pass `tools=` or `instructions=` later; `main.py` does not.

```text
main.py                       # one question; print report + metrics; score if JSON matches
investigator/agent.py         # name, default instructions/tools, model, output type
investigator/report.py        # InvestigationReport (summary + citations)
investigator/tools.py         # RepoContext + @function_tool wrappers
investigator/repo.py          # disk access (list, resolve, read, search, replace, run_tests); no SDK
investigator/metrics.py       # tokens, latency, cost, tool-call counts
investigator/score_report.py  # load_answer_keys; score one report vs one key
tests/                        # pytest for repo.py, metrics, report, scorer (no OpenAI)
sample_repos/inventory-app/   # investigation target (agent may read); planted bug
sample_answer_keys/inventory-app.json  # cases: Product + bulk discount (agent must not)
```

Current question in `main.py`: find the failing tests, fix them on the working copy with `replace_in_file`, re-run tests until they pass, then summarize.

That string is not in the JSON, so `python main.py` prints report + metrics and no score block. Read the report yourself. Put the Product question back if you want the citation score again. After a fix run, check `sample_repos/inventory-app/inventory/pricing.py`: it should still use `>` until you approve in 4.4. The copy under `workspaces/` may already have `>=`.

## What we built and how we checked it

### M0 — Hello agent

Minimal `Agent` + `Runner.run_sync`, no tools. Metrics printed after each run.

**Checked:** `python main.py` printed an answer; metrics showed `"requests": 1`. Traces: one `POST /v1/responses`; token counts matched. Cost matched a hand calculation from the pricing table (input × $0.10 + output × $0.50, per million tokens). Latency for the same call varied (about 3 s vs 9.5 s) because of provider-side wait, not our code.

### M1.1 — Sample project `inventory-app`

```text
sample_repos/inventory-app/     # folder given to the agent
├── README.md
├── pytest.ini
├── tests/
│   └── test_pricing.py         # qty 5 and 30 pass; qty 20 fails (two tests)
└── inventory/                  # importable package (name cannot contain '-')
    ├── products.py             # Product: sku, name, unit_price
    ├── stock.py                # Stock + OutOfStockError
    ├── pricing.py              # intended 10% off from 20 units; planted `>` bug
    └── orders.py               # place_order: stock then pricing
```

The outer name may use a hyphen; the inner package name may not (`import inventory-src` is invalid). The sample project is committed with this repo.

There was **no written answer key** in M1. M2 added `sample_answer_keys/inventory-app.json` (sibling of `sample_repos/`, never inside the shop). M3 added shop pytest tests and a planted comparison bug in `calculate_total`.

**Checked with a smoke test** from `sample_repos/inventory-app/` (imports work here; `python inventory/orders.py` does not):

```bash
python -c "
from inventory.products import Product
from inventory.stock import Stock, OutOfStockError
from inventory.orders import place_order
p = Product('MUG-01', 'Coffee mug', 5.0)
s = Stock(); s.add('MUG-01', 30)
print('small order:', place_order(s, p, 2).total, '| left:', s.available('MUG-01'))
print('order of 20 (planted bug, full price):', place_order(s, p, 20).total, '| left:', s.available('MUG-01'))
try:
    place_order(s, p, 50)
except OutOfStockError as e:
    print('too many:', e)
"
```

Expected: `10.0` / 28 left; `100.0` / 8 left; `OutOfStockError`. An order of exactly 20 units is full price until the planted `>` bug is fixed. Quantity 30 still gets 10% off (`135.0` for a $5 mug).

### M1.2 — `list_files`

A **tool** is a Python function the model may ask us to run. `@function_tool` (Agents SDK; not LangChain `@tool`) builds the schema from the name, types, and docstring. The SDK runs the function and sends the return string back to the model. That repeat is the **agentic loop**.

The folder is `RepoContext(source_root=..., workspace_root=...)` passed to `Runner.run_sync`. At start both paths are the same (the shop). Tools receive `ctx: RunContextWrapper[RepoContext]` and use `ctx.context.workspace_root`. The model never sees it (`list_files` schema has no parameters). `ctx` exists only while a tool runs; after the run, the same envelope is `result.context_wrapper`.

`repo.py` talks to the disk; `tools.py` only wraps it for the agent.

**Checked:**

```bash
python -c "from pathlib import Path; from investigator import repo; print(repo.list_files(Path('sample_repos/inventory-app')))"
python -c "from investigator.tools import list_files; print(list_files.name); print(list_files.description); print(list_files.params_json_schema)"
```

Expected: relative paths for the shop (including `pytest.ini` and `tests/test_pricing.py` after M3); schema `'properties': {}`. An earlier `python main.py` (question about files) listed all six files that existed then, `"requests": 2`, input tokens 64 → 281. Trace: `list_files` between two model turns; turn tokens summed to the printout.

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

### M1.4 — `search_code`

Literal, case-sensitive substring search over the same files as `list_files`. The model passes only the query. Hits look like `path:line: text`. Caps: 5 matches per file, 50 total. Empty query and zero matches return short strings.

### M1.5 — Structured output

The final reply is an `InvestigationReport`: `summary` plus `citations` (`path`, `start_line`, `end_line`). Shape only. Empty citations are allowed. Invalid JSON from the model stops the run.

For the current `QUESTION` in `main.py`, see **Current status** above.

### M1.6 — Tool-call metrics and pytest

`RunMetrics` includes `tool_calls` and `tool_calls_by_name`. pytest in `tests/` checks `repo.py`, cost math, and report fields. pytest does not call OpenAI.

### M2 — Score a report

**2.1** — `investigator/score_report.py`: load keys and `score_report`. pytest builds fake `InvestigationReport`s (no OpenAI). `python main.py` prints `--- Score ---` after a real run when `QUESTION` matches a JSON case.

**2.2** — The JSON is `{ "cases": [ Product, bulk discount ] }`. `load_answer_keys` returns a list. `score_report` still grades one report against one key. `build_agent` may take `tools=` and `instructions=`; defaults are unchanged.

M2 is the scorecard for those listed questions. Exam loops and prompt/tool variant grids are not part of this milestone.

### M3 — Failing-test investigation

The model may call `run_tests`. Our Python starts `python -m pytest -q` in the shop folder and returns the printed output as a string. The model does not get a shell and cannot choose the command. A failed pytest run is a normal string, like a missing file.

`calculate_total` in `inventory/pricing.py` uses `quantity > BULK_DISCOUNT_THRESHOLD` (planted bug). Shop tests: quantity 5 expects `25.0` (pass); quantity 20 expects `90.0` on both `calculate_total` and `place_order` (fail, code returns `100.0`); quantity 30 expects `135.0` (pass).

The agent is **agent-driven**: it calls `run_tests` when the question needs it. `main.py` does not run pytest first.

**Checked:** `pytest` from the project root; `python -m pytest -q` from `sample_repos/inventory-app/` shows 2 passed, 2 failed; `python main.py` with the failing-test question — agent called `run_tests`, cited `inventory/pricing.py`, explained `>` vs `>=` (no JSON score).

### M4.1–4.3 — Workspace, replace, one-run repair

The first `replace_in_file` copies the shop into `workspaces/<id>/`. Later tools in that run use the copy. `old_text` must appear exactly once. Python allows at most 8 `replace_in_file` calls per `python main.py`; the 9th returns an error string and does not write. Instructions tell the model to re-run tests after edits and stop when they pass. Approval (copy back to the original shop) is 4.4.

**Checked (no OpenAI):** `pytest` from the project root, including a 9th replace refused.

## Architecture and design decisions

Guiding rule: **the agent reasons and proposes; Python executes and enforces boundaries.**

| Area | Approach | Rationale |
| --- | --- | --- |
| Framework | Python + OpenAI Agents SDK | Learn agents, tools, and lifecycle before another orchestrator. |
| Interface | `main.py`; question and instructions in source | Agent behavior before CLI/UI. |
| Config | `.env` + `python-dotenv` | Secrets and model name stay out of code. |
| Dependencies | `requirements.txt` | Change only if a clear need arises. |
| Internal data | `@dataclass` (`RunMetrics`, `RepoContext`); Pydantic `InvestigationReport` | Dataclass for our records; Pydantic when the SDK validates the model's final reply. |
| Repo scope | Local, trusted Python first | Investigation before untrusted execution or GitHub. |
| Exploration | Custom list/read/search tools | Model pulls files on demand; we control path safety and size. |
| Tool context | SDK `RunContextWrapper` + `RepoContext` | We choose the folder; the model cannot. |
| File access | `repo.py` (disk) / `tools.py` (agent) | One place to harden later; tools stay thin. |
| Editing | Search-and-replace on a working copy (M4.2) | Unique snippet only; original files stay unchanged until approval (4.4). |
| Approval | Explicit human approval (from M4) | Required, not optional. |
| Orchestration | Agent-driven tests and repair; Python caps replaces at 8 per run | Model loops; Python enforces the fuse. |
| Evaluation | Scorecard for JSON-listed questions | Optional citation check; new prompts are judged by reading the report. |
| Observability | Tokens, estimated cost, latency, traces | Cost uses OpenAI list prices; traces confirm usage. |
| Integrations | MCP, GitHub, multi-agent, hosted tools later | When they enable a capability or a fair experiment. |

**Sync vs async (open):** `Runner.run_sync` now. `await Runner.run` when we need parallel evals, several users, streaming (`Runner.run_streamed`), or parallel agents. Threads are another option (sync code, several waiters). Decide when a need appears.

**Trusted repos vs original files:** trusting the sample code is not a claim that unknown repos are safe. `pytest` would run their code with local permissions. A working copy is not a sandbox.

**Local tools vs uploading a repo:** tools run here. Only the strings they return go to the model.

## Development roadmap

| Milestone | Scope | Definition of Done |
| --- | --- | --- |
| **M0 — Hello Agent** (completed) | Agent, Runner, config, metrics, tracing | `python main.py` prints answer + metrics; trace inspectable |
| **M1 — Repository Q&A** (completed) | list, read, search; Pydantic answers; pytest for tools | Questions about the sample project, including multi-file ones, with file references; tool tests pass; metrics include tool calls |
| **M2 — First evaluations** (completed) | Known-answer set, scorecard | Citation score for questions listed in the JSON |
| **M3 — Failing-test investigation** (completed) | `run_tests` on the shop; planted threshold bug | Agent can run shop pytest and explain the seeded failure |
| **M4 — Repair, retries, approval** | Working copy, bounded retries, diff, approval | Fixes seeded bugs; original unchanged without approval |
| **M5 — SDK patterns** | Guardrails, HITL, sessions | Experiments defined when this starts |
| **M6 — Multi-agent** | Handoffs vs agent-as-tool vs single agent | Compare with the eval suite |
| **M7 — MCP and GitHub** | MCP client and server, GitHub repos | Integration and safety criteria before coding |

**Next implementation step: M4.4** — after the agent run, diff, **required** human approval, then copy back or discard the workspace.

Deferred until needed: Ruff, GitHub Actions CI, `logging`, CLI/UI, Docker/E2B, prompt-injection defenses, RAG vs text search, LangGraph, secret-file denylist, pinning `requirements.txt`.
