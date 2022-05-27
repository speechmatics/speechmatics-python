SOURCES := speechmatics/ tests/ setup.py
VERSION ?= $(shell cat VERSION)

.PHONY: all
all: lint test docs

.PHONY: lint
lint:
	black $(SOURCES)
	pylint $(SOURCES)
	pycodestyle $(SOURCES) 

.PHONY: test
test: unittest

.PHONY: unittest
unittest:
	pytest -v tests/

.PHONY: build
build:
	VERSION=$(VERSION) python setup.py sdist bdist_wheel

.PHONY: docs
docs:
	sphinx-build -b html sphinx/ sphinx/_build
	$(RM) -r docs/*
	mv sphinx/_build/* docs/
