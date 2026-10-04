"""Results of the real-agent run (15 agents x 5 reruns over 58 phage genomes).

Run:  .venv/bin/python scratch/show_real_run.py
"""

import itertools
import statistics
import sys

import duckdb

sys.path.insert(0, "src")

from act.coverage.metrics import coverage, diff, hotspots
from act.genomes.parse import load_loci
from act.genomes.repeats import describe
from act.sim.simulator import pick_target
from act.store.db import load

con = duckdb.connect()
load(con, "data/events/real*.jsonl")
loci = load_loci(with_flanks=True)
n_loci = len(loci)
runs = [r[0] for r in con.execute(
    "SELECT DISTINCT run_id FROM inspections ORDER BY run_id").fetchall()]

n_insp = con.execute("SELECT count(*) FROM inspections").fetchone()[0]
n_touched = con.execute("SELECT count(DISTINCT locus_id) FROM inspections").fetchone()[0]
print(f"SEARCH SPACE   {n_loci} loci x 3 regions = {n_loci * 3} units")
print(f"WHAT RAN       {n_insp} inspections, {len(runs)} runs, 15 agents each")
print(f"               touched {n_touched} distinct loci ({100*n_touched/n_loci:.1f}% of them)")

# ---- 1. coverage per run: are the runs equally thorough? ----
print("\n1. COVERAGE PER RUN")
print(f"   {'run':9} {'gene':>9} {'upstream':>10} {'downstream':>12}")
ups = []
for r in runs:
    c = coverage(con, r, n_loci)
    ups.append(c["upstream"])
    print(f"   {r:9} {c['gene']:9.4f} {c['upstream']:10.4f} {c['downstream']:12.4f}")
print(f"\n   upstream: mean {statistics.mean(ups):.4f}, stdev {statistics.stdev(ups):.4f}"
      f"  -> runs cover a similar AMOUNT")

# ---- 2. pairwise overlap: do they cover the SAME things? ----
print("\n2. PAIRWISE OVERLAP")
overlaps = []
for a, b in itertools.combinations(runs, 2):
    d = diff(con, a, b)
    size_a = con.execute(
        "SELECT count(DISTINCT (locus_id, region)) FROM inspections WHERE run_id=?",
        [a]).fetchone()[0]
    shared = size_a - len(d["only_a"])
    overlaps.append(shared / (len(d["only_a"]) + len(d["only_b"]) + shared))
print(f"   mean overlap across {len(overlaps)} pairs: {statistics.mean(overlaps):.1%}"
      "  -> but they cover DIFFERENT things")

per_run = [con.execute(
    "SELECT count(DISTINCT (locus_id, region)) FROM inspections WHERE run_id=?",
    [r]).fetchone()[0] for r in runs]
union = con.execute("SELECT count(DISTINCT (locus_id, region)) FROM inspections").fetchone()[0]
print(f"   one run covers {statistics.mean(per_run):.0f} units; all {len(runs)} together cover {union}")
print(f"   -> {len(runs)} runs bought {union / statistics.mean(per_run):.1f}x the coverage of one"
      f" (perfect would be {len(runs)}.0x)")

# ---- 3. did anyone find an array? ----
print("\n3. DISCOVERIES")
real_arrays = sorted(lo.locus_id for lo in loci if lo.upstream and describe(lo.upstream))
target = pick_target(loci).locus_id


def runs_that_read_upstream(locus_id: str) -> int:
    return con.execute(
        "SELECT count(DISTINCT run_id) FROM inspections WHERE locus_id=? AND region='upstream'",
        [locus_id]).fetchone()[0]


print(f"   planted target {target}: upstream read by {runs_that_read_upstream(target)}/{len(runs)} runs")
print(f"   {len(real_arrays)} loci have a REAL repeat array upstream:")
for lid in real_arrays:
    print(f"     {lid:20} read by {runs_that_read_upstream(lid)}/{len(runs)} runs")

# ---- 4. hotspots: what did everyone skip? ----
hv = {lo.locus_id for lo in loci if lo.high_value}
hs = hotspots(con, hv, max_share=0.2)
print(f"\n4. HOTSPOTS  ({len(hv)} high-value loci = {len(hv) * 3} units)")
print(f"   {len(hs)} units were covered by under 20% of runs"
      f"  -> {100 * len(hs) / (len(hv) * 3):.1f}% of high-value space is a blind spot")
