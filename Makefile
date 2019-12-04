.PHONY: lint test all docs unittest functest

all: lint test docs

lint:
	pylint speechmatics/
	flake8 speechmatics/

test: unittest functest

unittest:
	pytest -v speechmatics/ tests/

functest:
	pytest -v speechmatics/ functests/

docs:
	sphinx-build -b html sphinx/ sphinx/_build
	rm -r docs/*
	mv sphinx/_build/* docs/
