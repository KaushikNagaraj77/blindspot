"""Agent event-logging logic, with a fake client (no API calls)."""

from types import SimpleNamespace

from act.agents.run import run_agent
from act.agents.tools import ToolEnv
from act.genomes.parse import synthetic_loci


def block(**kw):
    return SimpleNamespace(**kw)


class FakeClient:
    """Replays a scripted list of responses, recording what it was sent."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.sent = []
        self.messages = self

    def create(self, **kw):
        self.sent.append(kw)
        return self._responses.pop(0)


def resp(blocks, in_tok=100, out_tok=20):
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(
            input_tokens=in_tok, output_tokens=out_tok,
            cache_read_input_tokens=0, cache_creation_input_tokens=0,
        ),
    )


class NoBudget:
    def add(self, usage):
        pass


def test_note_comes_from_the_following_turn():
    """The agent comments after seeing the result, so the note is one turn later."""
    loci = synthetic_loci(50)
    env = ToolEnv(loci, loci[0].locus_id)
    client = FakeClient([
        resp([block(type="text", text="Let me look at this one."),
              block(type="tool_use", id="t1", name="inspect",
                    input={"locus_id": loci[3].locus_id, "region": "upstream"})]),
        resp([block(type="text", text="The upstream flank had nothing unusual.")]),
    ])
    events = run_agent(client, env, NoBudget(), "real00", 0, n_pages=2)

    assert len(events) == 1
    # NOT "Let me look at this one." -- that was written before the result came back.
    assert events[0]["note"] == "The upstream flank had nothing unusual."


def test_parent_is_a_real_inspect_task():
    """list_loci steps consume a step number but are not tasks, so they cannot be parents."""
    loci = synthetic_loci(50)
    env = ToolEnv(loci, loci[0].locus_id)
    client = FakeClient([
        resp([block(type="tool_use", id="t1", name="list_loci", input={"page": 0})]),
        resp([block(type="text", text="ok"),
              block(type="tool_use", id="t2", name="inspect",
                    input={"locus_id": loci[1].locus_id, "region": "gene"})]),
        resp([block(type="text", text="typical domains"),
              block(type="tool_use", id="t3", name="inspect",
                    input={"locus_id": loci[2].locus_id, "region": "upstream"})]),
        resp([block(type="text", text="nothing there")]),
    ])
    events = run_agent(client, env, NoBudget(), "real00", 0, n_pages=2)

    task_ids = {e["task_id"] for e in events}
    assert events[0]["parent_task_id"] is None          # first inspect has no parent
    assert events[1]["parent_task_id"] in task_ids      # parent exists in the log
    assert events[1]["parent_task_id"] == events[0]["task_id"]


def test_tokens_split_across_parallel_tool_calls():
    """One response's usage covers all its tool calls; don't bill each one the full amount."""
    loci = synthetic_loci(50)
    env = ToolEnv(loci, loci[0].locus_id)
    client = FakeClient([
        resp([block(type="tool_use", id="t1", name="inspect",
                    input={"locus_id": loci[1].locus_id, "region": "gene"}),
              block(type="tool_use", id="t2", name="inspect",
                    input={"locus_id": loci[2].locus_id, "region": "upstream"})],
             in_tok=100, out_tok=20),
        resp([block(type="text", text="done")]),
    ])
    events = run_agent(client, env, NoBudget(), "real00", 0, n_pages=2)

    assert len(events) == 2
    assert sum(e["tokens"] for e in events) <= 120  # not 240


def test_cache_breakpoint_is_on_the_conversation():
    """Haiku 4.5 needs a 4096-token prefix; the system prompt is far too short to cache."""
    loci = synthetic_loci(50)
    env = ToolEnv(loci, loci[0].locus_id)
    client = FakeClient([
        resp([block(type="tool_use", id="t1", name="list_loci", input={"page": 0})]),
        resp([block(type="text", text="done")]),
    ])
    run_agent(client, env, NoBudget(), "real00", 0, n_pages=2)

    second_call = client.sent[1]
    assert isinstance(second_call["system"], str)  # no breakpoint on the system prompt
    marked = [
        m for m in second_call["messages"]
        if isinstance(m.get("content"), list)
        and any(isinstance(b, dict) and "cache_control" in b for b in m["content"])
    ]
    assert len(marked) == 1


def test_missing_note_is_recorded_as_such():
    """An agent that stops without commenting leaves an honest marker, not ''."""
    loci = synthetic_loci(50)
    env = ToolEnv(loci, loci[0].locus_id)
    client = FakeClient([
        resp([block(type="tool_use", id="t1", name="inspect",
                    input={"locus_id": loci[1].locus_id, "region": "gene"})]),
        resp([]),  # stops with no text and no tool calls
    ])
    events = run_agent(client, env, NoBudget(), "real00", 0, n_pages=2)

    assert events[0]["note"] == "(no comment written)"
    assert events[0]["note_style"] == "missing"
