"""Local labeler plumbing, with a fake classifier (no model download)."""

import pytest

from act.labeler import zeroshot
from act.labeler.cache import JsonlCache

QS = {
    "read_upstream": {"type": "binary", "hypothesis": "Agent read upstream."},
    "region": {"type": "choice", "criteria": {"up": "upstream flank", "gene": "gene body"}},
}


def fake_clf(premises, candidate_labels, hypothesis_template, multi_label, batch_size, seen=None):
    """'upstream' in both note and label -> high score. Mimics the pipeline's list output."""
    outs = []
    for premise in premises:
        if seen is not None:
            seen.append(premise)
        scores = [0.9 if "upstream" in c and "upstream" in premise else 0.1
                  for c in candidate_labels]
        if not multi_label:
            scores = [s / sum(scores) for s in scores]
        pairs = sorted(zip(candidate_labels, scores), key=lambda t: -t[1])
        outs.append({"labels": [p[0] for p in pairs], "scores": [p[1] for p in pairs]})
    return outs


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(zeroshot, "_cache", JsonlCache(tmp_path / "c.jsonl"))


def test_binary_and_choice_shapes():
    a = zeroshot.ask("read the upstream flank", QS, classifier=fake_clf)
    assert a["read_upstream"]["choice"] == "yes"
    assert a["read_upstream"]["probabilities"] == pytest.approx({"yes": 0.9, "no": 0.1})
    assert a["region"]["choice"] == "up"
    assert abs(sum(a["region"]["probabilities"].values()) - 1) < 1e-9


def test_ask_many_keeps_order_and_only_runs_uncached():
    zeroshot.ask("read the upstream flank", QS, classifier=fake_clf)
    seen = []

    def spy(*args, **kw):
        return fake_clf(*args, **kw, seen=seen)

    out = zeroshot.ask_many(["read the upstream flank", "read the gene body"], QS, classifier=spy)
    assert [a["read_upstream"]["choice"] for a in out] == ["yes", "no"]
    assert set(seen) == {"read the gene body"}  # cached note never reached the model


def test_cache_hit_skips_classifier():
    first = zeroshot.ask("read the upstream flank", QS, classifier=fake_clf)

    def boom(*a, **k):
        raise AssertionError("classifier called on a cached input")

    assert zeroshot.ask("read the upstream flank", QS, classifier=boom) == first
