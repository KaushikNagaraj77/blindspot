"""DuckDB store. Loads JSONL event logs into `runs`, `tasks`, `inspections`.

`task_closure` is built by act.lineage.closure (a CORE file you write).

Usage: python -m act.store.db --load
"""

import argparse

import duckdb

from act.config import DB_PATH, EVENTS_DIR

def connect(path=DB_PATH) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path))


def load(con: duckdb.DuckDBPyConnection, glob: str | None = None) -> None:
    glob = glob or str(EVENTS_DIR / "*.jsonl")
    con.execute("DROP TABLE IF EXISTS events")
    con.execute("CREATE TABLE events AS SELECT * FROM read_json_auto(?)", [glob])

    con.execute("""
        CREATE OR REPLACE TABLE runs AS
        SELECT run_id, any_value(seed) AS seed,
               count(*) FILTER (WHERE role = 'planner') AS n_tasks,
               bool_or(outcome = 'found_candidate') AS found
        FROM events GROUP BY run_id
    """)
    con.execute("""
        CREATE OR REPLACE TABLE tasks AS
        SELECT task_id, parent_task_id, run_id, depth, agent_id, ts
        FROM events WHERE role = 'planner'
    """)
    # One row per planner step. `region` is ground truth; `note` is what a
    # real trace would contain. Labelers write predictions to other tables.
    con.execute("""
        CREATE OR REPLACE TABLE inspections AS
        SELECT run_id, task_id, locus_id, region, note, note_style, outcome, tokens
        FROM events WHERE role = 'planner'
    """)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    args = ap.parse_args()
    con = connect()
    if args.load:
        load(con)
        print(con.execute("SELECT * FROM runs ORDER BY run_id").fetchdf())
