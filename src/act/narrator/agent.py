"""Narrator loop. Wires Claude tool use to narrator.tools (CORE).

The model computes nothing: it can only call read-only tools, and every tool
result carries the query that produced it, which the narrator must cite.

Usage:
    python -m act.narrator.agent "which run covered the most upstream regions?"
"""

import argparse
import json

import anthropic

from act.config import ESCALATION_MODEL
from act.narrator.tools import TOOL_SCHEMAS, dispatch

MAX_STEPS = 8

SYSTEM = (
    "You explain agent-campaign coverage. Only state numbers returned by tools. "
    "Tag each claim 'VERIFIED' and cite the query from the tool result. "
    "State uncertainty and why. You cannot modify anything.\n\n"
    "Every tool result is {\"result\": ..., \"query\": ...}. When you state a "
    "number, write it as:\n"
    "  VERIFIED: <the claim>\n"
    "  query: <the query string from that result>\n\n"
    "If a tool gives you no number for something, say you do not know rather "
    "than estimating. Never compute a figure the tools did not return."
)


def ask(question: str, model: str = ESCALATION_MODEL, verbose: bool = False) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_STEPS):
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            return " ".join(b.text for b in resp.content if b.type == "text").strip()

        results = []
        for tu in tool_uses:
            if verbose:
                print(f"  [tool] {tu.name}({json.dumps(tu.input)})")
            out = dispatch(tu.name, tu.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(out, default=str),
            })
        messages.append({"role": "user", "content": results})

    return "(stopped: too many tool calls)"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--verbose", action="store_true", help="print each tool call")
    a = ap.parse_args()
    print(ask(a.question, verbose=a.verbose))
