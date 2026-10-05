# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Read-only tools the narrator can call.

Rules:
  - Code computes every number; the narrator only explains tool results.
  - No tool writes to the store. Open DuckDB read-only.
  - Every tool returns {"result": ..., "query": "<SQL or function call used>"}
    so the narrator can tag each claim VERIFIED with its evidence.

Tools to expose: coverage, diff, lineage (ancestors / path_to_discovery), hotspots.
"""

import duckdb

from act.config import DB_PATH
from act.coverage.metrics import coverage, diff, hotspots
from act.genomes.parse import load_loci
from act.lineage.closure import ancestors, build_closure, path_to_discovery

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "list_runs",
        "description": "List the campaign runs in the store, with task counts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "coverage",
        "description": (
            "What fraction of loci did one run inspect, split by region type "
            "(gene / upstream / downstream)? A unit is one (locus, region) pair."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "diff",
        "description": (
            "Where two runs diverged: the (locus, region) units each one "
            "inspected that the other never touched."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_a": {"type": "string"},
                "run_b": {"type": "string"},
                "limit": {"type": "integer", "description": "max examples to return"},
            },
            "required": ["run_a", "run_b"],
        },
    },
    {
        "name": "hotspots",
        "description": (
            "High-value units that few runs covered -- the blind spots. "
            "Returns (locus, region, share of runs that covered it)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_share": {
                    "type": "number",
                    "description": "flag units covered by less than this share of runs",
                },
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "path_to_discovery",
        "description": (
            "The chain of tasks from a root agent down to the task that found "
            "a candidate in one run, or null if that run found nothing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "ancestors",
        "description": "The tasks a given task descended from, nearest first.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
]


def _connect() -> duckdb.DuckDBPyConnection:
    """Read-only handle. The narrator must not be able to mutate the store."""
    return duckdb.connect(str(DB_PATH), read_only=True)


def _n_loci() -> int:
    """Denominator for coverage: the size of the whole search space."""
    return len(load_loci())


def dispatch(name: str, args: dict) -> dict:
    """Run one tool by name and return {"result", "query"}."""
    con = _connect()
    try:
        if name == "list_runs":
            rows = con.execute(
                "SELECT run_id, count(*) AS inspections, "
                "count(DISTINCT locus_id) AS loci "
                "FROM inspections GROUP BY run_id ORDER BY run_id"
            ).fetchall()
            return {
                "result": [
                    {"run_id": r[0], "inspections": r[1], "loci_touched": r[2]} for r in rows
                ],
                "query": "SELECT run_id, count(*), count(DISTINCT locus_id) "
                         "FROM inspections GROUP BY run_id",
            }

        if name == "coverage":
            run_id, n = args["run_id"], _n_loci()
            return {
                "result": coverage(con, run_id, n),
                "query": f"coverage(con, run_id={run_id!r}, n_loci={n})",
            }

        if name == "diff":
            a, b = args["run_a"], args["run_b"]
            limit = args.get("limit", 20)
            d = diff(con, a, b)
            return {
                "result": {
                    "only_a_count": len(d["only_a"]),
                    "only_b_count": len(d["only_b"]),
                    "only_a_examples": sorted(d["only_a"])[:limit],
                    "only_b_examples": sorted(d["only_b"])[:limit],
                },
                "query": f"diff(con, run_a={a!r}, run_b={b!r})",
            }

        if name == "hotspots":
            max_share = args.get("max_share", 0.2)
            limit = args.get("limit", 20)
            high_value = {lo.locus_id for lo in load_loci() if lo.high_value}
            hs = hotspots(con, high_value, max_share)
            return {
                "result": {
                    "count": len(hs),
                    "high_value_units": len(high_value) * 3,
                    "examples": [
                        {"locus_id": lo, "region": reg, "share_of_runs": share}
                        for lo, reg, share in sorted(hs)[:limit]
                    ],
                },
                "query": f"hotspots(con, high_value_loci=<{len(high_value)} loci>, "
                         f"max_share={max_share})",
            }

        if name in ("path_to_discovery", "ancestors"):
            # These read task_closure, which build_closure has to CREATE -- a
            # write the read-only handle cannot do. Copy the tables into an
            # in-memory database and build it there, so the store stays untouched.
            mem = _closure_copy(con)
            try:
                if name == "path_to_discovery":
                    run_id = args["run_id"]
                    return {
                        "result": path_to_discovery(mem, run_id),
                        "query": f"build_closure(con); path_to_discovery(con, {run_id!r})",
                    }
                task_id = args["task_id"]
                return {
                    "result": ancestors(mem, task_id),
                    "query": f"build_closure(con); ancestors(con, {task_id!r})",
                }
            finally:
                mem.close()

        return {"result": None, "query": f"unknown tool: {name}"}
    finally:
        con.close()


def _closure_copy(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    """In-memory copy of tasks + inspections with task_closure built on top."""
    mem = duckdb.connect()
    for table in ("tasks", "inspections"):
        rows = con.execute(f"SELECT * FROM {table}").fetchall()
        cols = [d[0] for d in con.execute(f"DESCRIBE {table}").fetchall()]
        mem.execute(f"CREATE TABLE {table} ({', '.join(f'{c} VARCHAR' for c in cols)})")
        if rows:
            mem.executemany(
                f"INSERT INTO {table} VALUES ({', '.join('?' * len(cols))})",
                [[None if v is None else str(v) for v in r] for r in rows],
            )
    build_closure(mem)
    return mem
