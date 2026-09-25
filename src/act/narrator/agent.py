"""Narrator loop (plumbing). Wires Claude tool use to narrator.tools (CORE).

Build this after narrator/tools.py works. Output contract for the system
prompt: every claim tagged VERIFIED with the query behind it, uncertainty
stated with its reason, and no write actions.
"""

SYSTEM = (
    "You explain agent-campaign coverage. Only state numbers returned by tools. "
    "Tag each claim 'VERIFIED' and cite the query from the tool result. "
    "State uncertainty and why. You cannot modify anything."
)


def ask(question: str) -> str:
    raise NotImplementedError("Build after narrator/tools.py (Phase 5).")
