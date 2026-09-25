# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Evaluation. Ground truth = inspections.region from the simulator (or the
agent tool log for real runs).

Report:
  1. tau sweep: escalation %, accuracy %, cost vs Claude-only %  (tau in 0.7, 0.8, 0.9, 0.95)
  2. Accuracy by q bucket (does confidence order the errors in YOUR data?)
  3. Accuracy split by note_style: explicit vs implicit
  4. Upstream-inspection recall from notes, at stated precision
  5. Real runs: variance of upstream coverage across the 5 reruns

Rules: invalid outputs count as errors; tau chosen on the selection split only.
"""


def tau_sweep(rows: list[dict], taus: list[float]) -> list[dict]:
    raise NotImplementedError


def accuracy_by_bucket(rows: list[dict], edges: list[float]) -> list[dict]:
    raise NotImplementedError


def recall_upstream(rows: list[dict]) -> dict:
    raise NotImplementedError
