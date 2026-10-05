"""Narrator tools: shape of the results, and the read-only guarantee."""

import duckdb
import pytest

from act.narrator import tools


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A tiny on-disk store, pointed at by the narrator's connect()."""
    path = tmp_path / "act.duckdb"
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE tasks AS SELECT * FROM (VALUES
            ('A', NULL, 'r1', 0), ('B', 'A', 'r1', 1), ('D', 'B', 'r1', 2)
        ) t(task_id, parent_task_id, run_id, depth)
    """)
    con.execute("""
        CREATE TABLE inspections AS SELECT * FROM (VALUES
            ('r1','A','L1','gene','rejected'),
            ('r1','B','L1','upstream','rejected'),
            ('r1','D','L3','upstream','found_candidate'),
            ('r2','X','L1','gene','rejected')
        ) t(run_id, task_id, locus_id, region, outcome)
    """)
    con.close()
    monkeypatch.setattr(tools, "DB_PATH", path)
    monkeypatch.setattr(tools, "_n_loci", lambda: 3)
    return path


def test_every_tool_schema_is_well_formed():
    names = {t["name"] for t in tools.TOOL_SCHEMAS}
    assert {"coverage", "diff", "hotspots", "path_to_discovery"} <= names
    for t in tools.TOOL_SCHEMAS:
        assert t["description"].strip()
        assert t["input_schema"]["type"] == "object"


def test_coverage_returns_result_and_query(store):
    out = tools.dispatch("coverage", {"run_id": "r1"})
    assert out["result"] == {"gene": 1 / 3, "upstream": 2 / 3, "downstream": 0.0}
    assert "r1" in out["query"]  # the narrator cites this


def test_diff_reports_both_directions(store):
    out = tools.dispatch("diff", {"run_a": "r1", "run_b": "r2"})
    assert out["result"]["only_a_count"] == 2  # (L1,upstream) and (L3,upstream)
    assert out["result"]["only_b_count"] == 0  # r2 read only (L1,gene), shared
    assert "query" in out


def test_path_to_discovery_builds_closure_without_touching_the_store(store):
    out = tools.dispatch("path_to_discovery", {"run_id": "r1"})
    assert out["result"] == ["A", "B", "D"]

    # The real store must still have no task_closure table.
    con = duckdb.connect(str(store), read_only=True)
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    con.close()
    assert "task_closure" not in tables


def test_ancestors(store):
    out = tools.dispatch("ancestors", {"task_id": "D"})
    assert out["result"] == ["B", "A"]


def test_unknown_tool_does_not_raise(store):
    out = tools.dispatch("drop_everything", {})
    assert out["result"] is None


def test_connection_is_read_only(store):
    con = tools._connect()
    with pytest.raises(duckdb.Error):
        con.execute("CREATE TABLE evil (x INT)")
    con.close()
