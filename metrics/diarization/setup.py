# -*- coding: utf-8 -*-
"""Package module."""

import os

from pip._internal.req import parse_requirements
from setuptools import find_packages, setup

requirements = parse_requirements("./requirements.txt", session=False)

git_tag = os.environ.get("CI_COMMIT_TAG")
if git_tag:
    assert git_tag.startswith("diarization-metrics")
version = git_tag.lstrip("diarization-metrics/") if git_tag else "0.0.3"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    author="Speechmatics",
    author_email="support@speechmatics.com",
    description="Python module for evaluating speaker diarization.",
    install_requires=[str(r.requirement) for r in requirements],
    name="speechmatics_diarization_metrics",
    license="Speechmatics Proprietary License",
    packages=find_packages(exclude=("tests",)),
    platforms=["linux"],
    python_requires=">=3.5",
    version=version,
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
)
