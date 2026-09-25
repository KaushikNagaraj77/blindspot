"""Simulated agent search campaign.

Planner agents pick (locus, region) pairs, reviewers check each task, and
tasks spawn subtasks at random. One high-value locus hides a repeat array in
its upstream flank. Reruns use different seeds, so some find it and some don't.

Every event carries the ground-truth `region` plus a free-text `note`.

Usage: python -m act.sim.simulator --reruns 10
"""

import argparse
import json
from datetime import UTC, datetime, timedelta

import numpy as np

from act.config import EVENTS_DIR
from act.genomes.parse import Locus, load_loci
from act.sim.notes import EXPLICIT, FOUND, IMPLICIT

DEFAULTS = {
    "n_roots": 40,  # top-level planner agents
    "p_spawn": 0.55,  # chance a task spawns each child
    "max_children": 2,
    "max_depth": 5,
    "region_probs": {"gene": 0.72, "downstream": 0.16, "upstream": 0.12},
    "p_high_value": 0.35,  # chance a task targets a high-value locus
    "p_implicit": 0.30,  # share of notes that only hint at the region
}


def pick_target(loci: list[Locus], seed: int = 0) -> Locus:
    """Planted discovery: fixed across reruns (seed 0), always a high-value locus."""
    hv = [loc for loc in loci if loc.high_value] or loci
    return hv[np.random.default_rng(seed).integers(len(hv))]


def run_campaign(run_id: str, seed: int, loci: list[Locus], target: Locus, **kw) -> list[dict]:
    p = {**DEFAULTS, **kw}
    rng = np.random.default_rng(seed)
    hv = [loc for loc in loci if loc.high_value] or loci
    regions = list(p["region_probs"])
    probs = list(p["region_probs"].values())
    t0 = datetime(2026, 9, 26, 9, 0, tzinfo=UTC)
    events: list[dict] = []
    counter = 0

    def new_task(parent_id: str | None, depth: int, agent_id: str) -> None:
        nonlocal counter
        counter += 1
        task_id = f"{run_id}-t{counter}"
        pool = hv if rng.random() < p["p_high_value"] else loci
        locus = pool[rng.integers(len(pool))]
        region = str(rng.choice(regions, p=probs))
        implicit = rng.random() < p["p_implicit"]
        templates = (IMPLICIT if implicit else EXPLICIT)[region]
        note = templates[rng.integers(len(templates))].format(gene=locus.gene, product=locus.product)

        found = locus.locus_id == target.locus_id and region == "upstream"
        if found:
            outcome = "found_candidate"
            note += FOUND
        else:
            outcome = str(
                rng.choice(
                    ["rejected", "inconclusive", "error_timeout", "error_tool"],
                    p=[0.7, 0.2, 0.06, 0.04],
                )
            )

        ts = t0 + timedelta(minutes=float(counter) * 1.3)
        base = {
            "run_id": run_id,
            "seed": seed,
            "task_id": task_id,
            "parent_task_id": parent_id,
            "depth": depth,
            "locus_id": locus.locus_id,
            "region": region,
            "note_style": "implicit" if implicit else "explicit",
            "tokens": int(rng.integers(800, 4000)),
        }
        events.append(
            {**base, "agent_id": agent_id, "role": "planner", "action": "inspect",
             "note": note, "outcome": outcome, "ts": ts.isoformat()}
        )
        events.append(
            {**base, "agent_id": f"{agent_id}-rev", "role": "reviewer", "action": "review",
             "note": f"Reviewed task {task_id}: {outcome}.", "outcome": outcome,
             "ts": (ts + timedelta(seconds=40)).isoformat()}
        )

        if depth < p["max_depth"]:
            for c in range(p["max_children"]):
                if rng.random() < p["p_spawn"]:
                    new_task(task_id, depth + 1, f"{agent_id}.{c}")

    for r in range(p["n_roots"]):
        new_task(None, 0, f"{run_id}-a{r}")
    return events


def main(reruns: int) -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    loci = load_loci(max_loci=2000)
    target = pick_target(loci)
    print(f"{len(loci)} loci; planted array upstream of {target.locus_id} ({target.product})")
    for i in range(reruns):
        run_id = f"sim{i:02d}"
        events = run_campaign(run_id, seed=1000 + i, loci=loci, target=target)
        out = EVENTS_DIR / f"{run_id}.jsonl"
        out.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        found = any(e["outcome"] == "found_candidate" for e in events)
        tasks = sum(e["role"] == "planner" for e in events)
        print(f"{run_id}: {tasks:4d} tasks  found={found}")
    (EVENTS_DIR / "target.json").write_text(json.dumps(target.to_dict(), indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reruns", type=int, default=10)
    main(ap.parse_args().reruns)
