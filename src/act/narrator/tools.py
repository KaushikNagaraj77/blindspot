# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Read-only tools the narrator can call.

Rules:
  - Code computes every number; the narrator only explains tool results.
  - No tool writes to the store. Open DuckDB read-only.
  - Every tool returns {"result": ..., "query": "<SQL or function call used>"}
    so the narrator can tag each claim VERIFIED with its evidence.

Tools to expose: coverage, diff, lineage (ancestors / path_to_discovery), hotspots.
"""

TOOL_SCHEMAS: list[dict] = []  # Anthropic tool definitions (name, description, input_schema)


def dispatch(name: str, args: dict) -> dict:
    """Run one tool by name and return {"result", "query"}."""
    raise NotImplementedError
