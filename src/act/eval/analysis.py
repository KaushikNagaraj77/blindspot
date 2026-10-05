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

A row is one labelled note:
    {"truth": "upstream", "pred": "upstream", "q": 0.96,
     "note_style": "implicit", "source": "sim"}
A row with q=None or pred=None is an invalid labeller output: it always
escalates, and counts as an error wherever the local label is scored.
"""

import itertools

# What one escalation costs, relative to labelling every note with Claude.
# The local model runs on our own hardware, so its marginal cost is ~0.
ESCALATION_COST = 1.0


def _is_invalid(row: dict) -> bool:
    return row.get("q") is None or row.get("pred") is None


def tau_sweep(rows: list[dict], taus: list[float]) -> list[dict]:
    """Cascade behaviour at each threshold.

    Accept the local label when q >= tau, otherwise escalate. Escalated notes
    are assumed correct, since Claude is the reference the cascade is measured
    against -- so accuracy here is "how much of Claude-only accuracy we keep".
    """
    n = len(rows)
    if n == 0:
        return []

    out = []
    for tau in taus:
        escalated = sum(1 for r in rows if _is_invalid(r) or r["q"] < tau)
        correct = sum(
            1 for r in rows
            if _is_invalid(r) or r["q"] < tau  # escalated -> Claude gets it right
            or r["pred"] == r["truth"]  # accepted -> right only if the label was
        )
        out.append({
            "tau": tau,
            "escalated": escalated,
            "escalation_rate": escalated / n,
            "accuracy": correct / n,
            "cost_vs_claude_only": escalated * ESCALATION_COST / n,
        })
    return out


def accuracy_by_bucket(rows: list[dict], edges: list[float]) -> list[dict]:
    """Accuracy within each confidence band.

    This is the cascade's load-bearing assumption: if accuracy does not climb
    with q, thresholding buys nothing and every note should go to Claude.
    Invalid rows have no q, so they are reported separately.
    """
    out = []
    for lo, hi in itertools.pairwise(edges):
        # The top bucket includes its upper edge, so q == 1.0 is not dropped.
        in_bucket = [
            r for r in rows
            if not _is_invalid(r) and lo <= r["q"] < hi or
            (hi == edges[-1] and not _is_invalid(r) and r["q"] == hi)
        ]
        correct = sum(1 for r in in_bucket if r["pred"] == r["truth"])
        out.append({
            "lo": lo,
            "hi": hi,
            "n": len(in_bucket),
            "accuracy": correct / len(in_bucket) if in_bucket else None,
        })

    invalid = [r for r in rows if _is_invalid(r)]
    if invalid:
        out.append({"lo": None, "hi": None, "n": len(invalid), "accuracy": 0.0})
    return out


def recall_upstream(rows: list[dict]) -> dict:
    """How many real upstream inspections the labeller recovers from notes.

    Recall is the number that matters for rebuilding coverage: a missed
    upstream read looks like a region nobody ever visited. Precision is
    reported alongside it, because recall alone can be bought by guessing
    "upstream" everywhere.
    """
    truth_up = [r for r in rows if r["truth"] == "upstream"]
    pred_up = [r for r in rows if not _is_invalid(r) and r["pred"] == "upstream"]
    hits = [r for r in truth_up if not _is_invalid(r) and r["pred"] == "upstream"]

    return {
        "n_truth_upstream": len(truth_up),
        "n_pred_upstream": len(pred_up),
        "true_positives": len(hits),
        "recall": len(hits) / len(truth_up) if truth_up else None,
        "precision": len(hits) / len(pred_up) if pred_up else None,
    }


def accuracy_by_style(rows: list[dict]) -> list[dict]:
    """Accuracy split by note_style -- explicit notes name the region, implicit
    ones only hint at it, and real agent notes are their own category."""
    styles = sorted({r["note_style"] for r in rows})
    out = []
    for style in styles:
        group = [r for r in rows if r["note_style"] == style]
        correct = sum(1 for r in group if not _is_invalid(r) and r["pred"] == r["truth"])
        out.append({
            "note_style": style,
            "n": len(group),
            "accuracy": correct / len(group) if group else None,
        })
    return out
