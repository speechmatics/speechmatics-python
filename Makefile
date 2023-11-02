SOURCES := speechmatics/ tests/ examples/ setup.py
VERSION ?= $(shell cat VERSION)

.PHONY: all
all: lint test docs

.PHONY: lint
lint:
	black --check --diff $(SOURCES)
	ruff $(SOURCES)

.PHONY: format
format:
	black $(SOURCES)

.PHONY: test
test: unittest

manual-test:
	speechmatics -v rt transcribe --url $(SM_URL) --ssl-mode regular --auth-token $(SM_AUTH_TOKEN) /tmp/example.wav

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
