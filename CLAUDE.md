# CLAUDE.md — Agent Campaign Coverage Tracker

## What this project is

A tool that shows what a large agent search campaign actually covered, and why reruns of the same campaign diverge.

Motivation: in Anthropic's public enzyme-discovery preprint (Sep 2026), ~950 agents searched sequence data for 21 hours. Ten reruns of the same campaign all missed the discovery because no rerun read the DNA upstream of the enzyme. This project makes that kind of coverage gap visible and measurable.

I am building this to learn. Treat me as a student on core files (see Working agreement).

## Architecture

1. `src/act/sim/` — campaign simulator. Synthetic agents over real public phage genomes; writes a JSONL event log with ground-truth `region` fields plus free-text `note` fields.
2. `data/genomes/` — 50–100 annotated phage genomes from NCBI (GenBank format), parsed with Biopython. Loci = annotated genes; regions = `gene`, `upstream`, `downstream` flanks.
3. `src/act/store/` — DuckDB. Tables: `runs`, `tasks`, `task_closure`, `inspections`.
4. `src/act/lineage/` — closure table build and queries (ancestors, descendants, path to discovery).
5. `src/act/coverage/` — `coverage(run_id)`, `diff(run_a, run_b)`, `hotspots()`.
6. `src/act/labeler/` — a local zero-shot NLI classifier labels each free-text note; low-confidence labels escalate to Claude. (Replaced the TypeSafe JEV API on 2026-09-25: signups paused. The cascade idea still comes from the JEV-as-a-Judge paper.)
7. `src/act/agents/` — real agent run: 15 Claude Haiku 4.5 agents × 5 reruns over the same genomes, with a structured tool that logs every region read.
8. `src/act/narrator/` — Claude with read-only SQL tools; every claim tagged VERIFIED with the query behind it.
9. `src/act/eval/` — τ sweep, accuracy by q bucket, explicit vs implicit notes, coverage recall.
10. `src/act/report/` — static HTML report.

## Working agreement (tutor mode)

### Core files — marked `# CORE` at the top
Current core files (all under `src/act/`): `lineage/closure.py`, `coverage/metrics.py`, `labeler/questions.py`, `labeler/cascade.py`, `narrator/tools.py`, `eval/analysis.py`. Their target tests are in `tests/` and fail until I implement them.

- Do NOT write or rewrite implementation code in these files.
- Explain concepts, give one hint at a time, and review my code by asking questions about bugs rather than fixing them.
- Only write a full solution if I type `/solution`, then explain it line by line.
- When I ask "why", answer with a tiny runnable example first (toy data, under 30 lines, in `scratch/`).

### Everything else
- You may write scaffolding, config, the simulator, genome download/parsing, API clients, retries, JSONL caching, logging, tests, plots, the HTML report, and README polish.
- Before writing, state in one line what you will write and which files it touches.

## Design rules (do not violate)

- Code computes every number (coverage, diffs, percentiles). The narrator LLM only explains tool results; it never computes.
- The narrator is read-only. No tool may write to the store or mutate runs.
- Cascade: accept the local classifier's label when q = max probability ≥ τ; otherwise escalate to Claude. Invalid output always escalates. Pick τ on a 20% selection split only; report on the held-out 80%.
- Count invalid outputs as errors in every eval.
- Pairwise classifier comparisons (if any) run in both orders and average the aligned probability.
- Use one question type per decision type; don't threshold `binary` and `choice` questions interchangeably. Pick τ per type.
- Never ask the classifier for forecasting, root-cause attribution across steps, or reference-free judgments.

## Cost controls (hard limits)

- Agents use `claude-haiku-4-5-20251001`. Do not switch models without asking me.
- Pilot first: 1 agent × 1 rerun, print total input/output tokens and estimated cost, then STOP and ask before the full run.
- Full run budget: ~$10–16. Enforce a `MAX_USD` env var (default 20) that aborts the run when exceeded.
- Cap each agent at 30 steps.
- Never send raw DNA sequences to an agent. Tools return compact summaries (coordinates, annotations, repeat-finder output).
- Use prompt caching for the system prompt and tool definitions.
- Cache every classifier and Claude response in JSONL; never re-call for an input already cached.

## Data and secrets

- All data is public (NCBI) or synthetic. No employer data, code, table names, or internal system names — ever.
- API keys come from `.env` only (`ANTHROPIC_API_KEY`). Never print, log, or commit them. `.env` is in `.gitignore`.

## Conventions

- Python 3.12, `uv` for environments, `ruff` for lint, `pytest` for tests.
- Every module gets a small test with a hand-checkable toy case (e.g., the A→B→D, A→C graph has 8 closure rows).
- Seeds are explicit and logged per run.

## Stretch (only after eval numbers exist)

- Critical path (CPM) over agent task timestamps to show which branch bottlenecked wall-clock time.
