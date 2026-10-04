"""Scratch pad for poking at the toy graph. Run: .venv/bin/python scratch/explore.py

Same data as tests/conftest.py, so whatever works here works in the tests.
"""

import duckdb

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

# Which tasks in run r1 read an upstream region?
con.sql("""
    SELECT task_id, run_id, region FROM inspections
    WHERE run_id = 'r1' AND region = 'upstream'
""").show()

#For every upstream read in r1, show which task did it and how deep that task was.
con.sql("""
    SELECT i.task_id , depth FROM inspections i 
    JOIN tasks t ON i.task_id = t.task_id 
    WHERE i.run_id = 'r1' AND i.region = 'upstream'

""").show()

#find all ancestors of D
con.sql("""
    SELECT t.parent_task_id FROM tasks t 
    WHERE t.task_id = 'D'


""").show()

#find all ancestors of D
con.sql("""
    WITH RECURSIVE anc AS (
    -- anchor: your first query, the one that gave you B
    SELECT t.parent_task_id 
    FROM tasks t
    WHERE t.task_id = 'D'

    UNION ALL

    -- recursive: join anc back to tasks on the condition you just described
    SELECT t.parent_task_id
    FROM anc
    JOIN tasks t ON anc.parent_task_id = t.task_id
)
SELECT * FROM anc;

""").show()

# build_closure: walk the tree once, store every (task, ancestor, depth) pair

con.execute("""

    CREATE OR REPLACE TABLE task_closure AS (
    WITH RECURSIVE closure AS(
    SELECT t.task_id , t.task_id as ancestor_id , 0 as depth  
    FROM tasks t

    UNION ALL

    SELECT  closure.task_id, t.parent_task_id , closure.depth + 1 as depth 
    FROM closure 
    JOIN tasks t ON closure.ancestor_id = t.task_id
    WHERE t.parent_task_id IS NOT NULL )
    
    SELECT * FROM closure 
    )
    
""")

con.sql(""" SELECT * FROM task_closure ORDER BY task_id, depth """).show()



# Toy data in tests/conftest.py — `inspections`:
#
#   run_id | task_id | locus_id | region     | outcome
#   -------+---------+----------+------------+----------------
#   r1     | A       | L1       | gene       | rejected
#   r1     | B       | L1       | upstream   | rejected
#   r1     | C       | L2       | gene       | rejected
#   r1     | D       | L3       | upstream   | found_candidate
#   r2     | X       | L1       | gene       | rejected
#   r2     | Y       | L2       | downstream | rejected
#
# coverage(con, "r1", n_loci=3) -> {"gene": 2/3, "upstream": 2/3, "downstream": 0.0}
#   gene:       L1, L2   -> 2 of 3 loci
#   upstream:   L1, L3   -> 2 of 3 loci
#   downstream: none     -> 0 of 3 loci

# region     | n
# -----------+---
# gene       | 2
# upstream   | 2


con.sql("""

SELECT region , COUNT(DISTINCT locus_id ) as n   FROM inspections WHERE  run_id = 'r1' GROUP BY region


""").show()

# ---- see what the metrics functions actually return ----
import sys
sys.path.insert(0, "src")
from act.coverage.metrics import coverage, diff

print("\ncoverage r1:", coverage(con, "r1", n_loci=3))
print("coverage r2:", coverage(con, "r2", n_loci=3))

d = diff(con, "r1", "r2")
print("only_a (r1 read, r2 missed):", sorted(d["only_a"]))
print("only_b (r2 read, r1 missed):", sorted(d["only_b"]))
