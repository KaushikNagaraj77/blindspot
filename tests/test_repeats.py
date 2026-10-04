"""Repeat finder, with hand-built sequences."""

import random

from act.genomes.repeats import describe, find_array

REPEAT = "CATGTGTATCGCAT"  # 14 bp, the K the finder uses


def spacer(n: int, seed: int = 0) -> str:
    """n bases of pseudo-random filler, so the filler itself has no repeats."""
    rng = random.Random(seed)
    return "".join(rng.choice("ACGT") for _ in range(n))


def test_finds_a_planted_array():
    # 4 copies, ~100 bp apart -- within the finder's spacing window
    seq = "".join(REPEAT + spacer(100, s) for s in range(4))
    a = find_array(seq)
    assert a is not None
    assert a.copies == 4
    assert all(100 <= s <= 130 for s in a.spacings)


def test_no_array_in_plain_filler():
    assert find_array(spacer(1200)) is None


def test_too_few_copies_is_not_an_array():
    seq = REPEAT + spacer(100, 1) + REPEAT + spacer(100, 2)  # only 2 copies
    assert find_array(seq) is None


def test_tandem_repeats_too_close_are_not_an_array():
    """Back-to-back copies are a microsatellite, not a spaced array."""
    assert find_array(REPEAT * 6 + spacer(400, 3)) is None


def test_describe_is_one_line_and_hides_the_sequence():
    seq = "".join(REPEAT + spacer(100, s) for s in range(3))
    out = describe(seq)
    assert out is not None
    assert "\n" not in out
    assert "3 copies" in out
    assert len(out) < 120  # compact enough for an agent's context


def test_describe_returns_none_when_there_is_nothing():
    assert describe(spacer(1200)) is None


def test_short_sequence_is_skipped():
    assert find_array("ACGT" * 10) is None
