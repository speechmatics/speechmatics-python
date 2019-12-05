.PHONY: lint test all docs unittest

all: lint test docs

lint:
	pylint speechmatics/
	flake8 speechmatics/

test: unittest

unittest:
	pytest -v speechmatics/ tests/

docs:
	sphinx-build -b html sphinx/ sphinx/_build
	rm -r docs/*
	mv sphinx/_build/* docs/
