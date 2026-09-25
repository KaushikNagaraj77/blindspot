"""Your target tests for lineage/closure.py (CORE). They fail until you implement it."""

from act.lineage.closure import ancestors, build_closure, descendants, path_to_discovery


def test_toy_closure_has_8_rows(toy_con):
    assert build_closure(toy_con) == 8


def test_ancestors_nearest_first(toy_con):
    build_closure(toy_con)
    assert ancestors(toy_con, "D") == ["B", "A"]


def test_descendants(toy_con):
    build_closure(toy_con)
    assert set(descendants(toy_con, "A")) == {"B", "C", "D"}


def test_path_to_discovery(toy_con):
    build_closure(toy_con)
    assert path_to_discovery(toy_con, "r1") == ["A", "B", "D"]
