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


def coverage(
    con: duckdb.DuckDBPyConnection, run_id: str, n_loci: int, source: str = "truth"
) -> dict[str, float]:
    """Return {'gene': x, 'upstream': y, 'downstream': z} as fractions of n_loci."""
    raise NotImplementedError


def diff(
    con: duckdb.DuckDBPyConnection, run_a: str, run_b: str, source: str = "truth"
) -> dict[str, set[tuple[str, str]]]:
    """Return {'only_a': {...}, 'only_b': {...}} of (locus_id, region) pairs."""
    raise NotImplementedError


def hotspots(
    con: duckdb.DuckDBPyConnection, high_value_loci: set[str], max_share: float = 0.2
) -> list[tuple[str, str, float]]:
    """(locus_id, region, share_of_runs_covering) for under-covered high-value units."""
    raise NotImplementedError
