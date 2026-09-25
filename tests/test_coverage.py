"""Your target tests for coverage/metrics.py (CORE)."""

from act.coverage.metrics import coverage, diff, hotspots


def test_coverage_by_region(toy_con):
    # r1 read gene of L1, L2; upstream of L1, L3; nothing downstream. 3 loci total.
    c = coverage(toy_con, "r1", n_loci=3)
    assert c == {"gene": 2 / 3, "upstream": 2 / 3, "downstream": 0.0}


def test_diff(toy_con):
    d = diff(toy_con, "r1", "r2")
    assert ("L3", "upstream") in d["only_a"]
    assert ("L2", "downstream") in d["only_b"]
    assert ("L1", "gene") not in d["only_a"]


def test_hotspots(toy_con):
    # L3 upstream is read by 1 of 2 runs (50%) -> not a hotspot at max_share=0.2
    # L3 downstream is read by 0 of 2 runs -> hotspot
    hs = {(loc, reg) for loc, reg, _ in hotspots(toy_con, {"L3"}, max_share=0.2)}
    assert ("L3", "downstream") in hs
    assert ("L3", "upstream") not in hs
