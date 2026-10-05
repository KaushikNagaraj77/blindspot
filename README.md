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

**Reruns converge on the same places, and more runs buy little.** Any two runs
shared **41%** of the units they inspected. That sounds like divergence until you
compare it to chance: a run covers 356 of 14,184 units, so two independent runs
would overlap about **2.5%**. The observed overlap is **16× that**. Independent
runs would have covered ~1,692 units between them; these five covered **704**.
Five runs bought **2.0×** the coverage of one, not 5×, because the agents are
drawn to the same regions rather than spreading out.

**Coverage is capped by the step budget, not by agent behaviour.** Every run's
median agent made exactly 30 inspections — the configured cap. 2.4% upstream
coverage is a fact about the budget (15 agents × 30 steps), not about how agents
search. **95% of all units were never inspected by any run**, which is why the
hotspot figure below is high.

**No run reached a target locus.** Five loci carry a genuine tandem repeat array
upstream; none was inspected, nor was the planted target. At 2.4% upstream
coverage this is the *expected* outcome — about 0.12 expected hits per run — so
it is not evidence of a systematic blind spot, only of a search space far larger
than the budget. It also differs in kind from the paper's failure: their reruns
*did* sample ART loci and two investigated the lineage, but none read far enough
upstream. This is a coverage-budget miss, not a read-depth miss.

**The cascade saves 32.5%, short of what it should.** It preserves accuracy
(97.7% against Claude-only's 100%) but escalates **67.5%** of notes at τ=0.7 —
two-thirds of traffic still goes to Claude, so the cheap stage is barely
working. The reason is visible below: 744 of 1,179 notes land in the lowest
confidence bucket. The local NLI model is under-confident on most real notes,
so nearly everything escalates. (For comparison, the JEV paper's cascade
escalated about a third.)

**Confidence does predict correctness**, which is the one assumption the cascade
needs:

| Local-model confidence | n | Accuracy |
| --- | --- | --- |
| 0.0–0.5 | 744 | 54.2% |
| 0.5–0.7 | 47 | 70.2% |
| 0.7–0.9 | 256 | 93.0% |
| 0.9–1.0 | 132 | 95.5% |

**What works and what doesn't.** Structured provenance from the tool log is
exact, and the coverage queries built on it are the part of this that works.
Reconstructing coverage from free-text notes **does not work yet**: 86% recall
at **34.8% precision** on real agent notes means recovered coverage would be
badly inflated. The templated-note scores (100%) are optimistic, since the
labeler's hypotheses were tuned against those exact templates.

**Caveats.** Five reruns is a small sample; the variance figures are descriptive,
not statistical claims. Coverage percentages are bounded by the step budget (see
above), so they describe this configuration rather than the harness in general.
Agents never see raw DNA, so this measures *coverage* — whether a region was
read — and not *recognition*, whether a model would notice an array it had read.
The paper tested recognition separately with a fixed-input benchmark.

**An engineering finding.** The NLI labeler matches on phrasing, not concept. A
hypothesis naming only the landmark ("before its start codon") scored ~0.98 on
notes phrased that way and ~0.06 on notes saying plainly "upstream of X" — an
almost exact 50/50 split, because the simulator alternates two templates per
region. Including both the bare term and the landmark in each hypothesis lifted
raw accuracy from 52.2% to 67.9%, and explicit-note accuracy from 47.7% to 100%.

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
