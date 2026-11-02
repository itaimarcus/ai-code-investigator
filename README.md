# AI Code Investigator

AI Code Investigator is a Python-based project for exploring software repositories, investigating failing tests, and developing agent-assisted code repair workflows.

The long-term goal is an agent that can gather evidence from a codebase, identify likely causes of failures, propose changes, validate them against tests, and request human approval before modifying the original repository.

The project is built incrementally using the **OpenAI Agents SDK**, with an emphasis on understandable architecture, observable behavior, and measurable results.

## Project goals

I am building this project to explore how AI agents can work with real developer tools and how to engineer them as reliable software systems.

My priorities are to:

- Understand agent execution, tool calling, context management, and the boundary between model decisions and application code.
- Design useful workflows for code exploration, debugging, and repair.
- Evaluate behavior using repeatable examples rather than relying solely on individual demonstrations.
- Experiment with technologies such as MCP, multi-agent orchestration, and retrieval when they serve a meaningful purpose.
- Apply software engineering practices progressively, without adding infrastructure before it is needed.

## Intended capabilities

The planned system will be able to:

- Explore Python repositories and answer questions with references to relevant files and lines.
- Investigate failing `pytest` tests and report likely root causes with supporting evidence.
- Propose code changes and apply them to a separate **working copy** of the repository.
- Run tests, interpret failures, revise proposed fixes, and stop after a bounded number of attempts.
- Present a diff for review and require **explicit human approval** before applying changes to the original repository.
- Measure answer quality, repair success, tool usage, latency, and API cost.
- Support GitHub repositories and explore GitHub integration through **Model Context Protocol (MCP)**.

These capabilities form the development roadmap; they are not all available in the initial implementation.

## Getting started

**Requirements:** Python 3.12, an OpenAI API key, and internet access for model calls.

From the project directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-6-luna
```

`.env` contains secrets and is excluded from version control by `.gitignore`.

Run the entry point:

```bash
python main.py
```

## Current status

Milestone **M0** is in progress. Running `main.py` sends a question defined in the code to a minimal agent and prints its answer.

```text
main.py                 # entry point: loads configuration, runs the agent, prints the result
investigator/agent.py   # agent definition: name, instructions, and model
```

`load_dotenv()` loads `.env` into the process environment. The OpenAI client used by the Agents SDK reads `OPENAI_API_KEY` from the environment automatically, so the key is never passed to the `Agent` in code. `OPENAI_MODEL` is an application-specific setting: `main.py` reads it and passes it to `build_agent(model)`. If either variable is missing, `main.py` stops with a clear error before making any API call.

## Architecture and design decisions

The following choices describe the intended direction. Decisions tied to later functionality remain open until their trade-offs can be assessed in practice.

| Area | Approach | Rationale |
| --- | --- | --- |
| Agent framework | Python + OpenAI Agents SDK | Work directly with agent execution, tools, and lifecycle concepts before introducing another orchestration framework. |
| Initial interface | Python entry point with input and instructions in source code | Prioritize agent behavior before building a CLI or UI. |
| Configuration | `.env` loaded with `python-dotenv` | Keep secrets and runtime settings, such as the model name, out of source code. |
| Dependencies | `requirements.txt` | Keep local setup straightforward; change dependency management only if a clear need arises. |
| Repository scope | Local, trusted Python repositories first | Develop investigation and test workflows before introducing remote repository integration or untrusted-code execution. |
| Code exploration | Dedicated, scoped file and search tools | Let the agent retrieve relevant information on demand instead of loading entire repositories into the model context. |
| Editing | Work on a separate copy, not the original repository | Allow iterative repair experiments while the original repository stays unchanged until a change is reviewed and approved. |
| Approval | Explicit human approval before applying a patch to the original | Keep consequential changes under user control. |
| Orchestration | Compare agent-driven, Python-driven, and hybrid workflows | Understand the trade-off between autonomy and predictable control before committing to one pattern. |
| Evaluation | Introduce small, repeatable evaluations early | Measure correctness and compare prompts, models, tools, and architectures. |
| Observability | Record token usage, estimated cost, latency, tool calls, and traces | Make agent behavior and operating costs understandable. |
| Advanced integrations | Add MCP, GitHub, multi-agent systems, and other tools incrementally | Use new technologies when they enable capabilities or useful architectural experiments. |

### Agent reasoning vs. deterministic application code

An important design boundary is the distinction between what the language model **decides** and what Python **enforces**.

**Agent decisions** may include choosing files to inspect, developing hypotheses about failures, interpreting test output, proposing patches, and deciding whether more investigation is warranted.

**Deterministic application code** handles file operations, repository path restrictions, test execution, working-copy management, approval checks, retry limits, and metric collection.

A useful guiding principle is: **the agent reasons and proposes; application code executes operations and enforces their boundaries.** This does not require a fully predetermined workflow. The degree of autonomy is itself a design choice to explore.

### Local tools and model context

Repository tools execute in Python. For example, a future `search_code` tool can search a local codebase and return matching filenames and line numbers. The model receives the returned tool output and may request additional files as needed.

Similarly, invoking `pytest` through a Python tool runs the tests locally; it does **not** automatically upload the repository to the model. Only the selected output returned by the tool, such as failing test names or relevant tracebacks, is passed to the agent. Files explicitly returned by read tools can also enter the model's context.

### Trusted repository scope and change protection

The initial development scope assumes repositories are owned or explicitly trusted. It does not include sandboxing arbitrary third-party code or comprehensive defenses against malicious repository content.

This is a **scope limitation**, not a claim that running unknown repositories is safe. `pytest` can execute arbitrary repository code with the permissions of the local process. Supporting untrusted sources would require revisiting execution isolation, credentials, and prompt-injection risks.

Protecting **original project files** is a separate requirement. Before edit capabilities are added, the agent has read-only tools. When repair functionality is introduced, changes will be made on a working copy and applied to the original only after human review and approval. A working copy prevents direct edits to the original; it is **not** a security sandbox.

File access and test execution should remain behind clear interfaces so their implementations can be strengthened later without unnecessarily coupling safety mechanisms to the agent logic.

## Development roadmap

Each milestone has a **Definition of Done (DoD)**: a small, verifiable outcome that establishes what the milestone should demonstrate.

| Milestone | Scope | Definition of Done |
| --- | --- | --- |
| **M0 — Hello Agent** | Minimal `Agent` and `Runner`; configuration, token usage, estimated API cost, latency, and tracing. | Running `python main.py` returns an answer and usage metrics, with an inspectable trace. |
| **M1 — Repository Q&A** | Read-only tools to list, read, and search local repository files; Pydantic structured responses; unit tests for tools. | Answer three predefined codebase questions with file references; tool tests pass; basic run metrics are available. |
| **M2 — First evaluations** | Small dataset of known-answer questions, automated scoring, and comparisons between model or instruction variants. | Produce a repeatable scorecard with success rate, cost, latency, and tool use; compare at least two variants. |
| **M3 — Failing-test investigation** | Run `pytest` on trusted sample repositories; produce a structured root-cause report; experiment with agent-driven and code-driven execution. | Identify the buggy function in seeded examples and evaluate the investigation results. |
| **M4 — Repair, retries, and approval** | Propose edits in a working copy, test and revise them within bounded attempts, present a diff, and require approval before applying changes to the original. | Repair seeded bugs; original files remain unchanged without approval; report repair rate and attempts. |
| **M5 — SDK workflow patterns** | Explore SDK guardrails, built-in human-in-the-loop approvals, and sessions for multi-turn investigations. | Establish specific experiments and acceptance criteria when this work begins. |
| **M6 — Multi-agent experiments** | Compare specialized agents, handoffs, and agent-as-tool patterns with a single-agent baseline. | Compare reliability, behavior, and resource usage using the evaluation suite. |
| **M7 — MCP and GitHub** | Consume external tools through MCP, expose investigator capabilities as an MCP server, and support GitHub repositories. | Define integration and execution-safety criteria before implementation. |

Additional explorations may include Ruff linting, GitHub Actions CI, richer logging, Docker-based isolation for untrusted code, RAG and embeddings compared with textual search, LangGraph, and a CLI or web UI. These are intentionally deferred until they add practical or educational value.
