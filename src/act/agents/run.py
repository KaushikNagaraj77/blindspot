"""Real agent run: N Claude Haiku 4.5 agents x R reruns over the same loci.

Always run the pilot first:
    python -m act.agents.run --pilot        (1 agent x 1 rerun, prints cost, stops)
    python -m act.agents.run --agents 15 --reruns 5

Events are written in the same schema as the simulator, so coverage, diff and
the labeler work unchanged. Ground truth comes from the tool log, not notes.
"""

import argparse
import json
from datetime import UTC, datetime

import anthropic

from act.agents.budget import Budget, BudgetExceeded
from act.agents.tools import PAGE_SIZE, TOOL_DEFS, ToolEnv
from act.config import AGENT_MODEL, EVENTS_DIR, MAX_STEPS_PER_AGENT
from act.genomes.parse import load_loci
from act.sim.simulator import pick_target

SYSTEM = (
    "You are one agent in a search campaign for interesting new reverse transcriptase "
    "systems in phage genomes.\n\n"
    "Tools: list_loci browses a page of genes; inspect reads one region of one gene "
    "('gene', 'upstream' or 'downstream').\n\n"
    "Work by inspecting, not browsing. Spend most of your calls on inspect. A gene's "
    "flanks are often more informative than its coding sequence, so check upstream and "
    "downstream regions as well as gene bodies.\n\n"
    "After each round of inspect calls, write one short sentence saying what you looked "
    "at and what you saw, before making your next calls. Keep going until you have "
    "examined many loci; stop only when you find something striking."
)


def run_agent(client, env: ToolEnv, budget: Budget, run_id: str, agent_idx: int,
              n_pages: int) -> list[dict]:
    """One agent's search. Returns its inspection events.

    The agent is told to comment after each inspect call, so its note arrives
    in the NEXT response, not the one that made the call. We hold the events
    from each turn and attach the following turn's text to them.
    """
    agent_id = f"{run_id}-a{agent_idx}"
    start_page = agent_idx % n_pages
    messages = [{"role": "user", "content": f"Start browsing at page {start_page}."}]
    events: list[dict] = []
    pending: list[dict] = []  # events still waiting for the agent's comment
    step = 0
    last_inspect_task: str | None = None  # parent must be a real task, not a list_loci step

    while step < MAX_STEPS_PER_AGENT:
        # Cache the conversation prefix, not the system prompt: Haiku 4.5 needs a
        # 4096-token minimum and SYSTEM + TOOL_DEFS is far short of it, so a
        # breakpoint there caches nothing (silently). The history does grow past it.
        cached = _with_cache_breakpoint(messages)
        resp = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=1200,  # 400 left no room for a comment plus tool calls
            system=SYSTEM,
            tools=TOOL_DEFS,
            messages=cached,
        )
        budget.add(resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        text = " ".join(b.text for b in resp.content if b.type == "text").strip()

        # This turn's text is the agent's comment on what it saw last turn.
        if text:
            for e in pending:
                e["note"] = text
            pending = []

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break

        # One response's tokens cover all of its tool calls; don't count them once each.
        per_call_tokens = (resp.usage.input_tokens + resp.usage.output_tokens) // len(tool_uses)

        results = []
        for tu in tool_uses:
            step += 1
            task_id = f"{agent_id}-s{step}"
            ctx = {"run_id": run_id, "task_id": task_id, "agent_id": agent_id}
            out = env.call(tu.name, tu.input, ctx)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            if tu.name == "inspect" and not out.startswith("error"):
                event = {
                    **ctx,
                    "seed": None,
                    "parent_task_id": last_inspect_task,
                    "depth": len(events),
                    "locus_id": tu.input["locus_id"],
                    "region": tu.input["region"],  # ground truth from the tool call
                    "note": "",  # filled in from the next response
                    "note_style": "agent",
                    "outcome": "found_candidate" if "repeat array" in out else "inspected",
                    "tokens": per_call_tokens,
                    "role": "planner",
                    "action": "inspect",
                    "ts": datetime.now(UTC).isoformat(),
                }
                events.append(event)
                pending.append(event)
                last_inspect_task = task_id
        messages.append({"role": "user", "content": results})

    # The agent stopped without commenting on its last inspections. Say so,
    # rather than leaving the labeler an empty string.
    for e in pending:
        e["note"] = "(no comment written)"
        e["note_style"] = "missing"
    return events


def _with_cache_breakpoint(messages: list[dict]) -> list[dict]:
    """Mark the end of the last tool-result message, so the history prefix is cached.

    Tool results are plain dicts we build ourselves; assistant turns are SDK
    objects, so the marker goes on the most recent user message.
    """
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        content = out[i].get("content")
        if out[i].get("role") == "user" and isinstance(content, list) and content:
            blocks = [dict(b) for b in content]
            blocks[-1]["cache_control"] = {"type": "ephemeral"}
            out[i] = {**out[i], "content": blocks}
            break
    return out


def main(n_agents: int, reruns: int, pilot: bool) -> None:
    if pilot:
        n_agents, reruns = 1, 1
    loci = load_loci(with_flanks=True)
    target = pick_target(loci)
    n_pages = max(1, len(loci) // PAGE_SIZE)
    client, budget = anthropic.Anthropic(), Budget()
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    def write(run_id: str, events: list[dict]) -> None:
        if events:
            (EVENTS_DIR / f"{run_id}.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events) + "\n")

    for r in range(reruns):
        run_id = f"real{r:02d}"
        env = ToolEnv(loci, target.locus_id)
        events: list[dict] = []
        try:
            for a in range(n_agents):
                events += run_agent(client, env, budget, run_id, a, n_pages)
                print(f"{run_id} agent {a}: {budget.summary()}")
        except BudgetExceeded as e:
            write(run_id, events)  # the money was spent; keep what it bought
            print(f"ABORTED: {e}")
            break
        write(run_id, events)

    print(f"TOTAL: {budget.summary()}")
    if pilot:
        full = budget.usd * 15 * 5
        print(f"Pilot done. Estimated full run (15 agents x 5 reruns): ~${full:.2f}. "
              "Check this before running `make agents`.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", type=int, default=15)
    ap.add_argument("--reruns", type=int, default=5)
    ap.add_argument("--pilot", action="store_true")
    a = ap.parse_args()
    main(a.agents, a.reruns, a.pilot)
