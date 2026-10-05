"""Eval functions, on hand-checkable toy rows."""

from act.eval.analysis import (
    accuracy_by_bucket,
    accuracy_by_style,
    recall_upstream,
    tau_sweep,
)
from act.labeler.cascade import pick_tau


def row(truth, pred, q, style="explicit"):
    return {"truth": truth, "pred": pred, "q": q, "note_style": style, "source": "sim"}


# 4 rows: 3 confident and right, 1 unsure and wrong.
ROWS = [
    row("upstream", "upstream", 0.95),
    row("gene", "gene", 0.92),
    row("downstream", "downstream", 0.91),
    row("upstream", "gene", 0.55),  # the error, and it is the least confident
]


def test_tau_sweep_low_tau_accepts_everything():
    (r,) = tau_sweep(ROWS, [0.5])
    assert r["escalated"] == 0
    assert r["accuracy"] == 0.75  # keeps the one wrong label
    assert r["cost_vs_claude_only"] == 0.0


def test_tau_sweep_mid_tau_escalates_only_the_error():
    (r,) = tau_sweep(ROWS, [0.9])
    assert r["escalated"] == 1
    assert r["accuracy"] == 1.0  # the wrong one went to Claude
    assert r["cost_vs_claude_only"] == 0.25  # paid for 1 of 4


def test_tau_sweep_high_tau_is_claude_only():
    (r,) = tau_sweep(ROWS, [1.0])
    assert r["escalation_rate"] == 1.0
    assert r["accuracy"] == 1.0
    assert r["cost_vs_claude_only"] == 1.0


def test_invalid_rows_always_escalate():
    rows = [*ROWS, row("gene", None, None)]
    (r,) = tau_sweep(rows, [0.0])  # tau=0 would accept any real q
    assert r["escalated"] == 1  # but the invalid one still escalates


def test_pick_tau_prefers_the_cheapest_that_holds_accuracy():
    # 0.9 reaches full accuracy; 0.95 also would, but escalates more.
    assert pick_tau(ROWS, [0.5, 0.9, 0.95], tolerance=0.02) == 0.9


def test_pick_tau_accepts_a_small_accuracy_loss_for_a_lower_tau():
    # With a 30-point tolerance, tau=0.5 (75% accurate) is good enough.
    assert pick_tau(ROWS, [0.5, 0.9, 0.95], tolerance=0.30) == 0.5


def test_accuracy_by_bucket_separates_confident_from_unsure():
    buckets = accuracy_by_bucket(ROWS, [0.5, 0.9, 1.0])
    low, high = buckets[0], buckets[1]
    assert (low["n"], low["accuracy"]) == (1, 0.0)    # the 0.55 row, wrong
    assert (high["n"], high["accuracy"]) == (3, 1.0)  # the three confident ones


def test_accuracy_by_bucket_reports_invalid_rows_separately():
    buckets = accuracy_by_bucket([*ROWS, row("gene", None, None)], [0.5, 1.0])
    invalid = buckets[-1]
    assert invalid["lo"] is None
    assert invalid["n"] == 1
    assert invalid["accuracy"] == 0.0  # invalid counts as an error


def test_recall_upstream():
    # 2 rows are truly upstream; the labeller caught 1 and called it right.
    r = recall_upstream(ROWS)
    assert r["n_truth_upstream"] == 2
    assert r["true_positives"] == 1
    assert r["recall"] == 0.5
    assert r["precision"] == 1.0  # it never said upstream when it was not


def test_accuracy_by_style():
    rows = [row("gene", "gene", 0.9, "explicit"), row("upstream", "gene", 0.6, "implicit")]
    by_style = {s["note_style"]: s for s in accuracy_by_style(rows)}
    assert by_style["explicit"]["accuracy"] == 1.0
    assert by_style["implicit"]["accuracy"] == 0.0
