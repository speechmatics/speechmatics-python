.PHONY: lint test all docs

all: lint test docs

lint:
	pylint speechmatics/
	flake8 speechmatics/

test:
	pytest -v speechmatics/ tests/ functests/

docs:
	sphinx-build -b html docs/ docs/_build/
