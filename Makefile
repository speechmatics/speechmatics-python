.PHONY: lint test all docs unittest

SOURCES := speechmatics/ setup.py

all: lint test docs

lint:
	pylint $(SOURCES)
	flake8 $(SOURCES)

test: unittest

unittest:
	pytest -v tests/

docs:
	sphinx-build -b html sphinx/ sphinx/_build
	$(RM) docs/*
	mv sphinx/_build/* docs/
