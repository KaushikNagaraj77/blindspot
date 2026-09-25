# Agent Campaign Coverage Tracker

Shows what a large agent search campaign actually covered, and why reruns of the same campaign diverge.

**Motivation.** In Anthropic's public enzyme-discovery work (Sep 2026), ~950 agents searched sequence data for 21 hours. Ten reruns of the same campaign all missed the discovery because none read the DNA upstream of the enzyme. This project makes that kind of coverage gap visible and measurable.

> Status: work in progress (weekend build). Results below will be filled in from the eval.

## What it answers

- Which parts of the search space did a run inspect, and how deeply?
- Which task spawned which, and which branch found the candidate?
- Where did run A and run B diverge?
- Which high-value regions are under-covered across runs?

## How it works

1. **Genomes** — 50–100 annotated public phage genomes (NCBI). Genes are loci; flanking sequence is `upstream` / `downstream`.
2. **Campaigns** — simulated agents (exact ground truth) plus a small real run: 15 Claude Haiku 4.5 agents × 5 reruns.
3. **Store** — DuckDB with a closure table for lineage.
4. **Coverage engine** — coverage by region type, run-to-run diff, under-covered hotspots.
5. **Cascade labeler** — a local zero-shot NLI model labels each free-text agent note; low-confidence labels escalate to Claude.
6. **Narrator** — Claude with read-only SQL tools; every claim is tagged VERIFIED with the query behind it.

## Results

| Metric | Value |
| --- | --- |
| Cascade labeling accuracy vs Claude-only | TBD |
| Cascade cost vs Claude-only | TBD |
| Upstream-flank inspections recovered from notes (recall @ precision) | TBD |
| Upstream coverage variance across real reruns | TBD |

## Quickstart

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env   # add your keys
make genomes           # download public phage genomes
make sim               # simulated campaign, 10 reruns
make test
```

## Influences

- A public OpenAI talk on pipeline lineage and SLAs (closure tables; code computes, the LLM explains; verified, read-only agents).
- Li et al., *JEV-as-a-Judge: Accept When Confident, Escalate When Unsure* (arXiv:2609.26550) — the confidence cascade (implemented here with a local NLI model in place of JEV).
- Anthropic's enzyme-discovery preprint — the rerun coverage problem.

All data is public or synthetic. This project makes no claims about how Anthropic's systems work internally.
