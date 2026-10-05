"""Run the labeler over agent notes and pair each prediction with the truth.

Produces the rows that eval/analysis.py consumes:

    {"truth": "upstream", "pred": "upstream", "q": 0.96,
     "note_style": "implicit", "source": "sim", "note": "..."}

`truth` is the ground-truth region the simulator recorded (or, for real runs,
the region the inspect tool was called with). `pred` and `q` come from the
local zero-shot labeler. Answers are cached, so a re-run is instant.

Usage:
    python -m act.eval.build_rows --n 1200
"""

import argparse
import json
import random
import time
from collections import defaultdict

from act.config import DATA, EVENTS_DIR
from act.labeler import zeroshot
from act.labeler.questions import build_premise, region_questions

ROWS_PATH = DATA / "eval_rows.jsonl"
KEY_TO_REGION = {"read_upstream": "upstream",
                 "read_downstream": "downstream",
                 "read_gene_body": "gene"}


def load_events() -> list[dict]:
    """Planner inspections from both the simulator and the real agent runs."""
    events = []
    for path in sorted(EVENTS_DIR.glob("*.jsonl")):
        source = "real" if path.stem.startswith("real") else "sim"
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("role") != "planner" or not e.get("note", "").strip():
                continue
            e["source"] = source
            events.append(e)
    return events


def stratified_sample(events: list[dict], n: int, seed: int = 0) -> list[dict]:
    """Even draw across (source, region, note_style), so every cell is populated."""
    buckets = defaultdict(list)
    for e in events:
        buckets[(e["source"], e["region"], e["note_style"])].append(e)

    rng = random.Random(seed)
    per_bucket = max(1, n // len(buckets))
    out = []
    for key in sorted(buckets):
        group = buckets[key]
        rng.shuffle(group)
        out.extend(group[:per_bucket])
    rng.shuffle(out)
    return out[:n]


def label(events: list[dict], batch_size: int = 16) -> list[dict]:
    """Ask the labeler about each note; keep the highest-scoring region as `pred`."""
    questions = region_questions()
    premises = [build_premise(e["note"], e.get("gene", "?"), e.get("product", "?"))
                for e in events]

    t0 = time.time()
    answers = zeroshot.ask_many(premises, questions, batch_size=batch_size)
    print(f"labelled {len(events)} notes in {time.time() - t0:.0f}s")

    rows = []
    for e, ans in zip(events, answers, strict=True):
        # One binary question per region: the winner is whichever says "yes" loudest.
        yes = {KEY_TO_REGION[k]: ans[k]["probabilities"]["yes"] for k in questions}
        pred = max(yes, key=yes.get)
        rows.append({
            "truth": e["region"],
            "pred": pred,
            "q": yes[pred],
            "note_style": e["note_style"],
            "source": e["source"],
            "run_id": e["run_id"],
            "locus_id": e["locus_id"],
            "note": e["note"],
        })
    return rows


def main(n: int) -> None:
    events = load_events()
    print(f"{len(events)} notes available")
    sample = stratified_sample(events, n)
    print(f"sampled {len(sample)}")

    rows = label(sample)
    ROWS_PATH.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    correct = sum(r["truth"] == r["pred"] for r in rows)
    print(f"\nwrote {ROWS_PATH}")
    print(f"raw accuracy (no cascade, no escalation): {correct}/{len(rows)} = "
          f"{correct / len(rows):.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200)
    main(ap.parse_args().n)
