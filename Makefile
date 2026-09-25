.PHONY: setup genomes sim load test lint pilot agents report clean

setup:            ## create venv and install
	uv venv --python 3.12 && uv pip install --python .venv -e ".[dev]"

genomes:          ## download ~60 public phage genomes from NCBI
	python -m act.genomes.fetch --n 60

sim:              ## simulated campaign, 10 reruns (works offline with synthetic loci)
	python -m act.sim.simulator --reruns 10

load:             ## load event logs into DuckDB
	python -m act.store.db --load

test:
	pytest -q

lint:
	ruff check src tests

pilot:            ## real agents: 1 agent x 1 rerun, prints cost, then stops
	python -m act.agents.run --pilot

agents:           ## real agents: 15 x 5 reruns (run pilot first!)
	python -m act.agents.run --agents 15 --reruns 5

report:
	python -m act.report.build

clean:
	rm -f data/act.duckdb data/events/*.jsonl
