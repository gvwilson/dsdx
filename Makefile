LESSONS = \
  crdt \
  distlock \
  eventual \
  mapreduce \
  msgque \
  oauth \
  tracing \
  worksteal

EXAMPLES_SRC = $(foreach dir,$(LESSONS),$(wildcard $(dir)/ex_*.py))
EXAMPLES_OUT = $(patsubst %.py,%.txt,${EXAMPLES_SRC})
SEED = 192837

.PHONY: docs

all: commands

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

## build: build package
build:
	python -m build

## check: check code issues
check:
	@ruff check ${LESSONS}

## clean: clean up
clean:
	@rm -rf ./dist
	@find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
	@find . -path ./.venv -prune -o -type d -name .ruff_cache -exec rm -rf {} +
	@find . -path ./.venv -prune -o -type f -name '*~' -exec rm {} +

## docs: build documentation
docs:
	@mccole build --src . --dst docs
	@touch docs/.nojekyll

## fix: fix code issues
fix:
	@ruff check --fix ${LESSONS}

## format: format code
format:
	@ruff format ${LESSONS}

## html: check HTML
html:
	@mccole check --src . --dst docs

## lint: run all code checks
lint:
	@make check
	@make types

## examples: regenerate example output
examples: ${EXAMPLES_OUT}

%.txt: %.py
	python $< ${SEED} > $@

## serve: serve documentation
serve:
	python -m http.server -d docs

## test: run tests
test:
	pytest tests

## types: check types
types:
	ty check ${LESSONS}
