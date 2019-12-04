.PHONY: lint test all docs

all: lint test docs

lint:
	pylint speechmatics/
	flake8 speechmatics/

test:
	pytest -v speechmatics/ tests/ functests/

docs:
	sphinx-build -b html sphinx/ sphinx/_build
	mv sphinx/_build/* docs/
