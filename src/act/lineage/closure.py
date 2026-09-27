# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Closure table for task lineage.

Concept: store every (descendant, ancestor) pair with its depth, including a
self-row at depth 0. Then "all ancestors of X" is one WHERE clause.

Toy check (A->B->D, A->C) = 8 rows:
    (A,A,0) (B,B,0) (C,C,0) (D,D,0)   self-rows
    (B,A,1) (C,A,1) (D,B,1) (D,A,2)   ancestor links

Target schema:
    task_closure(task_id, ancestor_id, depth, is_root, is_leaf)
      is_root: ancestor_id has no parent
      is_leaf: task_id has no children

Hint 1: a recursive CTE over `tasks(task_id, parent_task_id)` works in DuckDB.
Hint 2 (ask Claude Code for more, one at a time).
"""

import duckdb


def build_closure(con: duckdb.DuckDBPyConnection) -> int:
    """Create/replace `task_closure` from `tasks`. Return the row count."""
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


    return con.execute("SELECT count(*) FROM task_closure").fetchone()[0]
    



def ancestors(con: duckdb.DuckDBPyConnection, task_id: str) -> list[str]:
    """All ancestors of task_id, nearest first. Excludes the task itself."""
    rows =  con.execute("SELECT ancestor_id FROM task_closure WHERE task_id != ancestor_id AND task_id = ? ORDER BY depth",[task_id] ).fetchall()
        
    '''result = []
        for r in rows:
            result.append[r[0]]
        return result''' 
    
    return [ r[0] for r in rows]
    #raise NotImplementedError


def descendants(con: duckdb.DuckDBPyConnection, task_id: str) -> list[str]:
    """All descendants of task_id. Excludes the task itself."""
    rows =  con.execute("SELECT task_id FROM task_closure WHERE task_id != ancestor_id AND ancestor_id = ? ",[task_id] ).fetchall()
            
    '''result = []
            for r in rows:
                result.append[r[0]]
            return result''' 
        
    return [ r[0] for r in rows]



    #raise NotImplementedError


def path_to_discovery(con: duckdb.DuckDBPyConnection, run_id: str) -> list[str] | None:
    """Root-to-task path for the task whose outcome is 'found_candidate', or None."""
    row = con.execute("SELECT task_id FROM inspections WHERE outcome = 'found_candidate' AND run_id = ? ",[run_id] ).fetchone()
    if row is None:
        return None 
    rows = con.execute("SELECT ancestor_id from task_closure WHERE task_id = ? ORDER BY depth DESC",[row[0]]).fetchall()
    return [r[0] for r in rows]
    
    #raise NotImplementedError
