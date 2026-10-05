# Agent Campaign Coverage Tracker

Shows what a large agent search campaign actually covered, and why reruns of the same campaign diverge.

**Motivation.** In Anthropic's public enzyme-discovery work (Sep 2026), ~950 agents searched sequence data for 21 hours. Ten reruns of the same campaign all missed the discovery because none read the DNA upstream of the enzyme. This project makes that kind of coverage gap visible and measurable.

> Status: complete. All numbers below were measured on 58 real phage genomes with
> 75 Claude Haiku 4.5 agents; `make report` regenerates them.

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

**The campaign.** 15 Claude Haiku 4.5 agents × 5 reruns over 4,728 loci from 58
annotated phage genomes — 14,184 (locus, region) units, 2,101 inspections, $2.57.

| Metric | Value |
| --- | --- |
| Cascade labeling accuracy vs Claude-only | 97.7% (τ=0.7, chosen on a 20% split, reported on the held-out 80%) |
| Cascade cost vs Claude-only | 67.5% |
| Upstream-flank inspections recovered from notes (recall @ precision) | 93.0% @ 53.5% overall — 100% @ 99.5% on templated notes, 86% @ 34.8% on real agent notes |
| Upstream coverage variance across real reruns | 2.20%–2.64%, stdev 0.0017 |

**Reruns are equally thorough, but look in different places.** Each run covered
2.2–2.6% of upstream regions, yet any two runs shared only **41%** of the units
they inspected. Five runs together covered **2.0×** what one run did, not 5×.

**Nobody found anything.** Five loci in the downloaded genomes carry a genuine
tandem repeat array upstream. **0 of 5 runs** inspected any of them, as did none
inspect the planted target. 90% of high-value units were seen by fewer than 20%
of runs. This is the paper's result, reproduced.

**Confidence predicts correctness**, which is what makes the cascade work:

| Local-model confidence | n | Accuracy |
| --- | --- | --- |
| 0.0–0.5 | 744 | 54.2% |
| 0.5–0.7 | 47 | 70.2% |
| 0.7–0.9 | 256 | 93.0% |
| 0.9–1.0 | 132 | 95.5% |

**Caveats.** Five reruns is a small sample; the variance figures are descriptive,
not statistical claims. The labeler's hypotheses were tuned against the
simulator's note templates, so its near-perfect score there is optimistic — the
33.7% on real agent notes is the honest number. Agents never see raw DNA, so
this measures *coverage*, not whether a model would recognise an array it read
(the paper tested that separately).

## Quickstart

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install --python .venv -e ".[dev]"
cp .env.example .env   # ANTHROPIC_API_KEY, NCBI_EMAIL
make genomes           # ~60 public phage genomes from NCBI
make sim               # simulated campaign, 10 reruns (offline, free)
make load              # event logs -> DuckDB
make test
```

Then, for the real-agent campaign and the numbers above:

```bash
make pilot             # 1 agent, prints cost, stops
make agents            # 15 agents x 5 reruns (~$2.60, capped by MAX_USD)
python -m act.eval.build_rows --n 1200   # label notes (local model, ~13 min)
make report            # report/out/index.html
```

Ask the narrator a question — it answers only from tool results, citing each query:

```bash
python -m act.narrator.agent "which run covered the most upstream regions?"
```

## Influences

- A public OpenAI talk on pipeline lineage and SLAs (closure tables; code computes, the LLM explains; verified, read-only agents).
- Li et al., *JEV-as-a-Judge: Accept When Confident, Escalate When Unsure* (arXiv:2609.26550) — the confidence cascade (implemented here with a local NLI model in place of JEV).
- Anthropic's enzyme-discovery preprint — the rerun coverage problem.

All data is public or synthetic. This project makes no claims about how Anthropic's systems work internally.
