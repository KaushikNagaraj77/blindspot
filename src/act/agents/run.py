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
    "systems in phage genomes. Use list_loci to browse and inspect to read regions. "
    "After each inspect call, write one short sentence noting what you looked at and "
    "what you saw. Stop when you find something striking or run out of ideas."
)


def run_agent(client, env: ToolEnv, budget: Budget, run_id: str, agent_idx: int,
              n_pages: int) -> list[dict]:
    agent_id = f"{run_id}-a{agent_idx}"
    start_page = agent_idx % n_pages
    messages = [{"role": "user", "content": f"Start browsing at page {start_page}."}]
    events, step = [], 0

    while step < MAX_STEPS_PER_AGENT:
        resp = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=400,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOL_DEFS,
            messages=messages,
        )
        budget.add(resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        text = " ".join(b.text for b in resp.content if b.type == "text").strip()

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break

        results = []
        for tu in tool_uses:
            step += 1
            task_id = f"{agent_id}-s{step}"
            ctx = {"run_id": run_id, "task_id": task_id, "agent_id": agent_id}
            out = env.call(tu.name, tu.input, ctx)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            if tu.name == "inspect" and "error" not in out:
                events.append({
                    **ctx,
                    "seed": None,
                    "parent_task_id": f"{agent_id}-s{step - 1}" if step > 1 else None,
                    "depth": step - 1,
                    "locus_id": tu.input["locus_id"],
                    "region": tu.input["region"],  # ground truth from the tool call
                    "note": text,  # what the agent wrote (labeler input)
                    "note_style": "agent",
                    "outcome": "found_candidate" if "repeat array" in out else "inspected",
                    "tokens": resp.usage.input_tokens + resp.usage.output_tokens,
                    "role": "planner",
                    "action": "inspect",
                    "ts": datetime.now(UTC).isoformat(),
                })
        messages.append({"role": "user", "content": results})
    return events


def main(n_agents: int, reruns: int, pilot: bool) -> None:
    if pilot:
        n_agents, reruns = 1, 1
    loci = load_loci(max_loci=2000)
    target = pick_target(loci)
    n_pages = max(1, len(loci) // PAGE_SIZE)
    client, budget = anthropic.Anthropic(), Budget()
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        for r in range(reruns):
            run_id = f"real{r:02d}"
            env = ToolEnv(loci, target.locus_id)
            events = []
            for a in range(n_agents):
                events += run_agent(client, env, budget, run_id, a, n_pages)
                print(f"{run_id} agent {a}: {budget.summary()}")
            (EVENTS_DIR / f"{run_id}.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events) + "\n")
    except BudgetExceeded as e:
        print(f"ABORTED: {e}")

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
