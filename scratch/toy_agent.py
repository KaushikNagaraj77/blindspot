"""Toy agent: 5 shelves, one has 'GOLD' buried in filler. Two tools: a cheap
peek (describe_shelf) and an expensive full read (read_shelf). Shows the
same gap this whole project is about: an agent can *touch* something
without ever *reading* it closely enough to notice what's in it.
"""

import random

import anthropic

import act.config  # noqa: F401  (side effect: loads .env)

random.seed(0)
FILLER = "The warehouse creaked. Dust settled on old crates. " * 12
SHELVES = {i: FILLER for i in range(5)}
SHELVES[3] = FILLER[:300] + "GOLD" + FILLER[300:]  # buried in the middle
SUMMARIES = {0: "mostly old papers", 1: "broken furniture", 2: "empty boxes",
             3: "mostly old papers", 4: "cleaning supplies"}  # shelf 3 looks boring on purpose

TOOLS = [
    {"name": "describe_shelf", "description": "One-line summary of a shelf.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}},
    {"name": "read_shelf", "description": "Full contents of a shelf.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}},
]

touched, read_full = set(), set()


def call_tool(name: str, shelf_id: int) -> str:
    if name == "describe_shelf":
        touched.add(shelf_id)
        out = f"shelf {shelf_id}: {SUMMARIES[shelf_id]}"
    else:
        touched.add(shelf_id)
        read_full.add(shelf_id)
        out = SHELVES[shelf_id]
    print(f"  [{name}] shelf {shelf_id} -> {len(out)} chars")
    return out


client = anthropic.Anthropic()
messages = [{"role": "user", "content": "Find anything valuable in the warehouse (5 shelves, ids 0-4)."}]

for _ in range(10):  # step cap
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=300, tools=TOOLS, messages=messages)
    messages.append({"role": "assistant", "content": resp.content})
    tool_uses = [b for b in resp.content if b.type == "tool_use"]
    if not tool_uses:
        print("FINAL:", " ".join(b.text for b in resp.content if b.type == "text"))
        break
    results = [{"type": "tool_result", "tool_use_id": tu.id,
                "content": call_tool(tu.name, tu.input["id"])} for tu in tool_uses]
    messages.append({"role": "user", "content": results})

print("touched shelves:  ", sorted(touched))
print("fully read shelves:", sorted(read_full))
