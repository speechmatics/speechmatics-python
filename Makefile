.PHONY: lint test all docs unittest

SOURCES := speechmatics/ setup.py tests
VERSION ?= $(shell cat VERSION).dev0

all: lint test docs

lint:
	pylint $(SOURCES)
	flake8 $(SOURCES)
	pycodestyle $(SOURCES)

test: unittest

unittest:
	pytest -v tests/

build:
	VERSION=$(VERSION) python setup.py sdist bdist_wheel

docs:
	sphinx-build -b html sphinx/ sphinx/_build
	$(RM) -r docs/*
	mv sphinx/_build/* docs/
