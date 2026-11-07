PROJECT ?= your-gcp-project
DATASET ?= basketpulse
BUCKET  ?= your-bucket
LOCATION ?= US

.PHONY: setup install test lint data-dev data-standard data-xl load build dry-run bench estimate

install:
	pip install -r requirements-dev.txt

test:
	python -m pytest -q

lint:
	python scripts/lint_lookml.py

data-dev:
	python -m datagen.generate --profile dev --out data/dev

data-standard:
	python -m datagen.generate --profile standard --out data/standard

data-xl:
	python -m datagen.generate --profile xl --out data/xl

load:
	python scripts/load_data.py --project $(PROJECT) --bucket $(BUCKET) --dataset $(DATASET) --data data/$(DATA)

dry-run:
	python scripts/run_sql.py --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION) --dry-run

setup:
	python scripts/run_sql.py --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION) --setup

build:
	python scripts/run_sql.py --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION)

bench:
	python benchmarks/bench.py --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION) --runs 5

estimate:
	python benchmarks/estimate.py --days 730 --transactions 50000000

# Additive operations; the original build/load targets retain their behavior.
.PHONY: ops-check ops-refresh
ops-check:
	python -m operations.runner --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION) --action check --start-date $(START_DATE) --end-date $(END_DATE)

ops-refresh:
	python -m operations.runner --project $(PROJECT) --dataset $(DATASET) --location $(LOCATION) --action refresh --start-date $(START_DATE) --end-date $(END_DATE)
