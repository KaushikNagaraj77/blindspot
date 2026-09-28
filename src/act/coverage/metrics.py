# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Coverage, run diffs, and under-covered hotspots.

Unit of coverage: a (locus_id, region) pair. A run "covered" a unit if any
of its inspections touched it.

    coverage = covered units / total units, split by region type

Run diff = set difference over (locus_id, region) pairs.

Hotspot = a high-value unit that fewer than `max_share` of runs covered.
Stretch: weight hotspots by value, not just raw coverage (the talk's
"rank by time saved at the leaf" idea, applied to discovery value).

`source` lets you compute the same metrics from ground truth
('truth' -> inspections.region) or from labeler predictions ('labels').
Comparing the two is how you measure the labeler.
"""

import duckdb

from act.config import REGIONS

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


def coverage(
    con: duckdb.DuckDBPyConnection, run_id: str, n_loci: int, source: str = "truth"
) -> dict[str, float]:
    """Return {'gene': x, 'upstream': y, 'downstream': z} as fractions of n_loci."""
    result = {r: 0.0 for r in REGIONS} 
    rows = con.execute("""

    SELECT region , COUNT(DISTINCT locus_id ) as n   FROM inspections WHERE  run_id = ? GROUP BY region


    """,[run_id]).fetchall()
    for r in rows:
        result[r[0]] = r[1]/n_loci

    return result

    #raise NotImplementedError


# Same `inspections` table as above:
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
# The (locus_id, region) pairs each run covered:
#   r1:  (L1, gene)   (L1, upstream)   (L2, gene)   (L3, upstream)
#   r2:  (L1, gene)   (L2, downstream)
#
# diff(con, "r1", "r2") -> {
#     "only_a": {("L1","upstream"), ("L2","gene"), ("L3","upstream")},
#     "only_b": {("L2","downstream")},
# }
#   (L1, gene) is in BOTH runs, so it appears in neither set.


def diff(
    con: duckdb.DuckDBPyConnection, run_a: str, run_b: str, source: str = "truth"
) -> dict[str, set[tuple[str, str]]]:
    """Return {'only_a': {...}, 'only_b': {...}} of (locus_id, region) pairs."""
    rows_a =  con.execute(""" SELECT  DISTINCT locus_id , region FROM  inspections  where run_id = ? """,[run_a]).fetchall()
    rows_b =  con.execute(""" SELECT  DISTINCT locus_id , region FROM  inspections  where run_id = ? """,[run_b]).fetchall()

    set_a = set(rows_a)
    set_b = set(rows_b)
    return {"only_a": set_a - set_b, "only_b": set_b - set_a}


    
    #raise NotImplementedError


# Same `inspections` table. Two runs exist in the toy data: r1 and r2.
#
# hotspots(con, high_value_loci={"L3"}, max_share=0.2)
#
# The candidate units are every (high-value locus x region) combination:
#
#   locus | region     | runs that covered it | share | hotspot?
#   ------+------------+----------------------+-------+---------
#   L3    | gene       | none                 | 0.0   | yes
#   L3    | upstream   | r1                   | 0.5   | no  (0.5 >= 0.2)
#   L3    | downstream | none                 | 0.0   | yes
#
# Note (L3, gene) and (L3, downstream) appear in NO row of `inspections`.
# The candidate list cannot come from the table alone -- it has to be built
# from high_value_loci x REGIONS.


def hotspots(
    con: duckdb.DuckDBPyConnection, high_value_loci: set[str], max_share: float = 0.2
) -> list[tuple[str, str, float]]:
    """(locus_id, region, share_of_runs_covering) for under-covered high-value units."""
    results = []
    total_runs = con.execute(""" SELECT Count(DISTINCT run_id) FROM inspections  """).fetchone()[0]
    for locus in high_value_loci:
        for region in REGIONS:
            n = con.execute(""" SELECT Count(DISTINCT run_id) FROM inspections WHERE locus_id = ? AND region = ?  """,[locus , region]).fetchone()[0]
            share = n / total_runs
            if share < max_share:
                results.append((locus, region, share))

    return results




    #raise NotImplementedError
