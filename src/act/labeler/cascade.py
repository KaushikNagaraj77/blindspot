# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Accept-or-escalate cascade (from the JEV-as-a-Judge paper).

Rule: q = max label probability. Accept JEV's label if q >= tau, otherwise
escalate to Claude. Invalid JEV output (missing answer, bad payload) ALWAYS
escalates, and counts as an error in eval.

Pick tau on a 20% selection split only. Report on the held-out 80%.
Paper's threshold rule: the lowest tau that keeps selection-set accuracy
within 2 points of the fallback while maximizing JEV coverage.
"""

from dataclasses import dataclass


@dataclass
class Decision:
    label: str | bool | None
    q: float | None
    source: str  # "jev" | "claude" | "invalid"
    escalated: bool


def max_prob(answer: dict) -> float | None:
    """q for one JEV answer. Return None if the answer is invalid."""
    raise NotImplementedError


def decide(jev_answer: dict | None, tau: float, escalate_fn) -> Decision:
    """Apply the cascade to one question. escalate_fn() returns Claude's label."""
    raise NotImplementedError


def pick_tau(selection_rows: list[dict], taus: list[float], tolerance: float = 0.02) -> float:
    """Choose tau on the selection split using the paper's rule."""
    raise NotImplementedError
