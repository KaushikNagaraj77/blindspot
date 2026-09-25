"""Your target tests for labeler/cascade.py (CORE)."""

from act.labeler.cascade import decide, max_prob


def test_max_prob():
    ans = {"choice": "a", "probabilities": {"a": 0.8, "b": 0.2}}
    assert max_prob(ans) == 0.8


def test_invalid_answer_escalates():
    d = decide(None, tau=0.9, escalate_fn=lambda: "b")
    assert d.escalated and d.label == "b"


def test_confident_answer_accepted():
    ans = {"choice": "a", "probabilities": {"a": 0.95, "b": 0.05}}
    d = decide(ans, tau=0.9, escalate_fn=lambda: "b")
    assert not d.escalated and d.label == "a"


def test_unsure_answer_escalates():
    ans = {"choice": "a", "probabilities": {"a": 0.6, "b": 0.4}}
    d = decide(ans, tau=0.9, escalate_fn=lambda: "b")
    assert d.escalated and d.label == "b"
