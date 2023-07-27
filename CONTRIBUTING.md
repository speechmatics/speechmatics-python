# Contributing

Welcome to the Speechmatics Python SDK and CLI! We're open to contributions from anyone. We hope you can find everything you need in here to get started contributing to this repo.

## Table of Contents

- [Useful Links](#useful-links)
- [Setting Up](#setting-up)
- [How to Submit Changes](#how-to-submit-changes)
- [How to Report a Bug](#how-to-report-a-bug)
- [How to Request a Feature](#how-to-request-a-feature)
- [Style Guide](#style-guide)
- [Testing](#testing)
- [Releasing](#releasing)

## Useful Links

- [Speechmatics Website](https://www.speechmatics.com/)
- [Portal (for generating API keys)](https://portal.speechmatics.com/manage-access/)
- [Docs](https://docs.speechmatics.com/)

## Setting Up

To get started, make sure you have a compatible version of python installed. Currently, we support 3.7-3.10.

To install the dependencies for development run:

```
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## How to Submit Changes

We try not to be too prescreptive about how people work, but we also believe in helping make things easier by following a couple of basic steps. If you follow these recommendations, it should make the review process simpler and quicker:

1. If your change is large, consider reaching out to us beforehand and discussing the issue. This could save you a lot of time if there are good reasons why we haven't done something.
2. Make sure your changes are tested - ideally both manually and in the unit tests.
3. When opening a PR, provide some simple descriptive comments that list the changes being made in the PR.
4. Give your PR a short, descriptive title.

## How to Report a Bug

If you are experiencing a bug, you can report it via the [issues](https://github.com/speechmatics/speechmatics-python/issues) page. Ideally, you'd follow our [template](./BUG_REPORT.md) for submitting bugs to make it easier for us to understand and respond to the report. Make sure to tag your issue with the bug label. And remember, the more details you give us, the better we can understand and fix your problem!

## How to Request a Feature

If you want a feature, you can open a discussion via the [issues](https://github.com/speechmatics/speechmatics-python/issues) page. Try to tag your issue with the most appropriate label available so that we can track it more easily.

When requesting a feature, we don't have a particule template we expect you to follow. Just make sure that you include as much information as possible about the feature you'd like to see added, why you'd like to see it added and what the expected behaviour of the feature might be.

## Style Guide

> Any color you like.

As with many python projects, ours uses [Black](https://pypi.org/project/black/) to set the standard for formatting. We also use [ruff](https://astral.sh/ruff) to handle our linting. We previously used pylint, but we love the lightning-fast performance that the rust-based linter provides us!

You can run linting and formatting using the makefile:

```
make format
make lint
```

We also make use of the [pre-commit](https://pre-commit.com/) package. This should already be installed when you clone the repo. If it isn't installed, you can install it by running the `pre-commit install`. It will run a serious of checks on every commit to make sure your code is properly formatted and linted. You can run the pre-commit check independent of a commit with the command `pre-commit run --all-files`.

In general, code should be self-explanatory and kept as simple as possible. Comments can be added to clarify what a piece of code does and docstrings should be added to any important functions that are expected to be used by SDK clients.

## Testing

Tests for this repo are included in the `/tests` directory. You can use the command `make unittests` to run unit tests. You can also target specific tests using the pytest command, e.g.:

```
pytest -v tests/test_models.py::test_notification_config
```

If you make changes to the SDK or CLI, the tests should be updated or added to in a sensible way to ensure the new change is properly covered.

## Releasing

To release your changes, you should create a tag with the version of the release as it's name. This takes the format X.Y.Z e.g. 1.9.0. Once the tag is created, create and publish a new release from the new tag. This should automatically trigger a GitHub action that will publish your changes to PyPi.

Note: GitHub workflow runs on `released`. This means it triggers when a release is published, or a pre-release is updated to a release. Drafts will do nothing.
