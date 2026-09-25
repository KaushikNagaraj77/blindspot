import duckdb
import pytest


@pytest.fixture
def toy_con():
    """Toy graph A->B->D, A->C in one run. Hand-checkable."""
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE tasks AS SELECT * FROM (VALUES
            ('A', NULL, 'r1', 0),
            ('B', 'A',  'r1', 1),
            ('C', 'A',  'r1', 1),
            ('D', 'B',  'r1', 2)
        ) t(task_id, parent_task_id, run_id, depth)
    """)
    con.execute("""
        CREATE TABLE inspections AS SELECT * FROM (VALUES
            ('r1', 'A', 'L1', 'gene',     'rejected'),
            ('r1', 'B', 'L1', 'upstream', 'rejected'),
            ('r1', 'C', 'L2', 'gene',     'rejected'),
            ('r1', 'D', 'L3', 'upstream', 'found_candidate'),
            ('r2', 'X', 'L1', 'gene',     'rejected'),
            ('r2', 'Y', 'L2', 'downstream','rejected')
        ) t(run_id, task_id, locus_id, region, outcome)
    """)
    return con
