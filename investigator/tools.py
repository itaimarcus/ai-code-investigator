from dataclasses import dataclass
from pathlib import Path

from agents import RunContextWrapper, function_tool

from investigator import repo


@dataclass
class RepoContext:
    root: Path


@function_tool
def list_files(ctx: RunContextWrapper[RepoContext]) -> str:
    """List all files in the repository, as paths relative to the repository root."""
    return "\n".join(repo.list_files(ctx.context.root))
