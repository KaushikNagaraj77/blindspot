"""Tandem repeat finder for flanking regions.

Method follows the paper's k-mer scan: take the most frequent k-mers in the
window, locate copies allowing one mismatch, and keep the longest run of
copies at near-constant spacing.

Agents never see the sequence itself -- `describe` returns a one-line summary.
"""

from collections import Counter
from dataclasses import dataclass

K = 14  # repeat word length
MIN_COPIES = 3
MIN_SPACING, MAX_SPACING = 60, 450  # start-to-start, in bases


@dataclass
class Array:
    word: str
    copies: int
    spacings: list[int]


def _mismatches(a: str, b: str, cap: int = 1) -> int:
    n = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            n += 1
            if n > cap:
                return n
    return n


def find_array(seq: str) -> Array | None:
    """Longest run of >=3 regularly spaced copies of a recurring k-mer, or None."""
    seq = seq.upper()
    if len(seq) < 200:
        return None

    counts = Counter(seq[i:i + K] for i in range(len(seq) - K + 1))
    for word, n in counts.most_common(12):
        if n < 2 or len(set(word)) < 3:
            continue

        positions, i = [], 0
        while i <= len(seq) - K:
            if _mismatches(seq[i:i + K], word) <= 1:
                positions.append(i)
                i += K
            else:
                i += 1
        if len(positions) < MIN_COPIES:
            continue

        run = [positions[0]]
        for p in positions[1:]:
            if MIN_SPACING <= p - run[-1] <= MAX_SPACING:
                run.append(p)
            elif len(run) >= MIN_COPIES:
                break
            else:
                run = [p]

        if len(run) >= MIN_COPIES:
            return Array(word, len(run), [run[i + 1] - run[i] for i in range(len(run) - 1)])
    return None


def describe(seq: str) -> str | None:
    """One-line summary of an array in `seq`, or None if there is none."""
    a = find_array(seq)
    if a is None:
        return None
    lo, hi = min(a.spacings), max(a.spacings)
    span = "" if lo == hi else f"-{hi}"
    return (f"tandem repeat array: {a.copies} copies of a {K}-bp repeat "
            f"({a.word}), spacers {lo}{span} bp")
