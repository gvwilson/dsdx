# Runnable tasks.

SLUG=dsdx

all: commands

HTML_IGNORES = 'Attribute "x-' 'Attribute "@click' 'Attribute "file"'

## build: build HTML
build:
	mccole build
	@touch docs/.nojekyll

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

## clean: clean up
clean:
	@find . -type f -name '*~' -exec rm {} \;
	@find . -type d -name __pycache__ | xargs rm -r
	@find . -type d -name .ruff_cache | xargs rm -r

## links: check links in published site
links:
	linkchecker -F text https://gvwilson.github.io/${SLUG}/

## lint: check code and project
lint:
	@mccole lint --html

## serve: serve generated HTML
serve:
	@python -m http.server -d docs $(PORT)

## spelling: check for unknown words
spelling:
	@cat *.md */*.md | aspell list | sort | uniq | diff - extras/words.txt
