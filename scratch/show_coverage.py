"""See your Phase 3 functions on the real 10-run simulation.

Run:  .venv/bin/python scratch/show_coverage.py
(If there is no data yet:  .venv/bin/python -m act.sim.simulator --reruns 10)
"""

import json
import sys

import duckdb

sys.path.insert(0, "src")

from act.coverage.metrics import coverage, diff, hotspots
from act.store.db import load

con = duckdb.connect()
load(con, "data/events/sim*.jsonl")

target = json.load(open("data/events/target.json"))
tid = target["locus_id"]
n_loci = con.execute("SELECT count(DISTINCT locus_id) FROM inspections").fetchone()[0]

print(f"Planted discovery: upstream of {tid} ({target['product']})")
print(f"{n_loci} loci inspected across 10 runs\n")

# ---- coverage: every run reads gene bodies far more than upstream flanks ----
print("COVERAGE PER RUN")
print(f"  {'run':7} {'gene':>7} {'upstream':>9} {'downstream':>11}   found?")
for (r,) in con.execute("SELECT DISTINCT run_id FROM inspections ORDER BY run_id").fetchall():
    c = coverage(con, r, n_loci)
    found = con.execute(
        "SELECT bool_or(outcome='found_candidate') FROM inspections WHERE run_id=?", [r]
    ).fetchone()[0]
    print(f"  {r:7} {c['gene']:7.3f} {c['upstream']:9.3f} {c['downstream']:11.3f}   {found}")

# ---- diff: what did the winning run read that a failing one did not? ----
print("\nDIFF  sim08 (found it)  vs  sim03 (missed it)")
d = diff(con, "sim08", "sim03")
print(f"  sim08 read {len(d['only_a'])} units sim03 never touched")
print(f"  sim03 read {len(d['only_b'])} units sim08 never touched")
print(f"  ({tid}, upstream) in only_a?  {(tid, 'upstream') in d['only_a']}")

# ---- hotspots: valuable places almost nobody looked ----
hv = {r[0] for r in con.execute("SELECT DISTINCT locus_id FROM inspections LIMIT 60").fetchall()}
hv.add(tid)
hs = hotspots(con, hv, max_share=0.2)
print(f"\nHOTSPOTS  ({len(hv)} high-value loci, flagged if < 20% of runs covered it)")
print(f"  {len(hs)} under-covered units found. The target's:")
for locus, region, share in sorted(hs):
    if locus == tid:
        print(f"    {locus}  {region:10}  share={share}")
