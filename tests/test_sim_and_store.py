"""Plumbing tests — these should pass out of the box."""

import json

import duckdb

from act.genomes.parse import synthetic_loci
from act.sim.simulator import pick_target, run_campaign
from act.store.db import load


def test_simulator_is_reproducible():
    loci = synthetic_loci(300)
    target = pick_target(loci)
    a = run_campaign("r", seed=7, loci=loci, target=target)
    b = run_campaign("r", seed=7, loci=loci, target=target)
    assert a == b


def test_found_only_on_target_upstream():
    loci = synthetic_loci(300)
    target = pick_target(loci)
    for seed in range(20):
        for e in run_campaign("r", seed, loci, target):
            if e["outcome"] == "found_candidate":
                assert e["locus_id"] == target.locus_id and e["region"] == "upstream"


def test_store_loads(tmp_path):
    loci = synthetic_loci(300)
    target = pick_target(loci)
    events = run_campaign("r1", seed=1, loci=loci, target=target)
    f = tmp_path / "r1.jsonl"
    f.write_text("\n".join(json.dumps(e) for e in events))
    con = duckdb.connect()
    load(con, str(f))
    n_tasks = con.execute("SELECT count(*) FROM tasks").fetchone()[0]
    assert n_tasks == sum(e["role"] == "planner" for e in events)
