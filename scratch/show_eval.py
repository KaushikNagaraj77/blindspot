"""The eval report: tau sweep, confidence buckets, note styles, upstream recall.

Run:  .venv/bin/python scratch/show_eval.py
Needs data/eval_rows.jsonl -- build it with:
      .venv/bin/python -m act.eval.build_rows --n 1200
"""

import json
import random
import sys

sys.path.insert(0, "src")

from act.config import DATA
from act.eval.analysis import (
    accuracy_by_bucket,
    accuracy_by_style,
    recall_upstream,
    tau_sweep,
)
from act.labeler.cascade import pick_tau

TAUS = [0.7, 0.8, 0.9, 0.95]
rows = [json.loads(line) for line in (DATA / "eval_rows.jsonl").read_text().splitlines()]

# 20% to choose tau on, 80% held out to report on. Never swap these.
random.Random(0).shuffle(rows)
split = len(rows) // 5
selection, holdout = rows[:split], rows[split:]

raw = sum(r["pred"] == r["truth"] for r in rows) / len(rows)
print(f"{len(rows)} labelled notes  ({len(selection)} selection / {len(holdout)} held out)")
print(f"raw local-model accuracy, no cascade: {raw:.1%}\n")

# ---- 1. tau sweep on the held-out split ----
print("1. TAU SWEEP (held-out split)")
print(f"   {'tau':>5} {'escalated':>10} {'accuracy':>9} {'cost vs Claude-only':>20}")
for r in tau_sweep(holdout, TAUS):
    print(f"   {r['tau']:5.2f} {r['escalation_rate']:10.1%} {r['accuracy']:9.1%} "
          f"{r['cost_vs_claude_only']:20.1%}")

chosen = pick_tau(selection, TAUS)
at_chosen = next(r for r in tau_sweep(holdout, [chosen]))
print(f"\n   tau chosen on the SELECTION split: {chosen}")
print(f"   reported on the HELD-OUT split: {at_chosen['accuracy']:.1%} of Claude-only "
      f"accuracy at {at_chosen['cost_vs_claude_only']:.1%} of its cost")

# ---- 2. does confidence order the errors? ----
print("\n2. ACCURACY BY CONFIDENCE BUCKET")
print(f"   {'bucket':>14} {'n':>6} {'accuracy':>9}")
for b in accuracy_by_bucket(rows, [0.0, 0.5, 0.7, 0.9, 1.0]):
    label = "invalid" if b["lo"] is None else f"{b['lo']:.1f}-{b['hi']:.1f}"
    acc = "-" if b["accuracy"] is None else f"{b['accuracy']:.1%}"
    print(f"   {label:>14} {b['n']:6} {acc:>9}")
print("   (if accuracy does not climb with confidence, thresholding buys nothing)")

# ---- 3. explicit vs implicit vs real agent notes ----
print("\n3. ACCURACY BY NOTE STYLE")
print(f"   {'style':>10} {'n':>6} {'accuracy':>9}")
for s in accuracy_by_style(rows):
    acc = "-" if s["accuracy"] is None else f"{s['accuracy']:.1%}"
    print(f"   {s['note_style']:>10} {s['n']:6} {acc:>9}")

# ---- 4. can we rebuild upstream coverage from notes alone? ----
r = recall_upstream(rows)
print("\n4. UPSTREAM RECOVERY FROM NOTES")
print(f"   {r['n_truth_upstream']} notes were really upstream; "
      f"the labeller found {r['true_positives']}")
print(f"   recall {r['recall']:.1%} at precision {r['precision']:.1%}")

sim = [x for x in rows if x["source"] == "sim"]
real = [x for x in rows if x["source"] == "real"]
for name, group in [("simulator", sim), ("real agents", real)]:
    if group:
        g = recall_upstream(group)
        print(f"   {name:12} recall {g['recall']:.1%}  precision {g['precision']:.1%}  "
              f"(n={g['n_truth_upstream']})")
