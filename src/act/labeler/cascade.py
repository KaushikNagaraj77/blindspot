# CORE — you write this. Claude Code: tutor mode only (see CLAUDE.md).
"""Accept-or-escalate cascade (from the JEV-as-a-Judge paper).

Rule: q = max label probability. Accept the local classifier's label if
q >= tau, otherwise escalate to Claude. Invalid output (missing answer, bad payload) ALWAYS
escalates, and counts as an error in eval.

Pick tau on a 20% selection split only. Report on the held-out 80%.
Paper's threshold rule: the lowest tau that keeps selection-set accuracy
within 2 points of the fallback while maximizing local-classifier coverage.
"""

from dataclasses import dataclass


@dataclass
class Decision:
    label: str | bool | None
    q: float | None
    source: str  # "local" | "claude" | "invalid"
    escalated: bool


def max_prob(answer: dict) -> float | None:
    """q for one classifier answer. Return None if the answer is invalid."""

    if answer is None or not answer.get("probabilities") :
        return None

    return max(answer["probabilities"].values())

    #raise NotImplementedError


def decide(answer: dict | None, tau: float, escalate_fn) -> Decision:
    """Apply the cascade to one question. escalate_fn() returns Claude's label."""
    q = max_prob(answer)
    if q is None:
        label = escalate_fn()
        return Decision(label=label,q=None,source="invalid",escalated=True)
    if q >= tau:
        return Decision(label=answer["choice"],q=q,source="local",escalated=False)
    
    if q < tau:
        label=escalate_fn()
        return Decision(label=label,q=q,source="claude",escalated=True)

    


    #raise NotImplementedError


def pick_tau(selection_rows: list[dict], taus: list[float], tolerance: float = 0.02) -> float:
    """Choose tau on the selection split using the paper's rule.

    The lowest tau whose accuracy stays within `tolerance` of the fallback
    (escalating everything, i.e. Claude-only). Lowest means cheapest, since
    fewer notes escalate. Call this on the 20% selection split only -- picking
    tau on the data you then report would be grading your own homework.
    """
    from act.eval.analysis import tau_sweep  # local import: eval imports cascade

    sweep = tau_sweep(selection_rows, sorted(taus))
    if not sweep:
        return max(taus)

    # Escalating everything is the ceiling: by construction its accuracy is 1.0,
    # because escalated notes are scored as Claude getting them right.
    fallback = max(row["accuracy"] for row in sweep + [{"accuracy": 1.0}])

    for row in sweep:  # ascending tau -> first match is the cheapest
        if row["accuracy"] >= fallback - tolerance:
            return row["tau"]
    return max(taus)
