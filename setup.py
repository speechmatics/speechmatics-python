#!/usr/bin/env python3
"""
Setuptools configuration for Speechmatics
"""

import os
import logging

from setuptools import setup


def read(fname):
    """
    Load content of the file with path relative to where setup.py is.

    Args:
        fname (str): file name (or path relative to the project root)

    Returns:
        str: file content
    """
    fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
    retval = open(fpath).read()

    return retval


def read_list(fname):
    """
    Load content of the file and split it into a list of lines.

    Args:
        fname (str): file name (or path relative to the project root)

    Returns:
        List[str]: file content (one string per line) with end of lines characters stripped off
                   and empty lines filtered out
    """
    content = read(fname)
    retval = list(filter(None, content.split('\n')))

    return retval


def get_version(fname):
    """
    Retrieve version from the VERSION file.

    Args:
        fname (str): file containing only the version

    Returns:
        str: version with whitespace characters stripped off
    """
    return read(fname).strip()


logging.basicConfig(level=logging.INFO)

setup(
    name='speechmatics-python',
    version=get_version('VERSION'),
    packages=['speechmatics'],
    url='https://github.com/speechmatics/speechmatics-python.git',
    license='MIT',
    author='Speechmatics',
    author_email='support@speechmatics.com',
    description='Python API client for Speechmatics',
    long_description=read('README.md'),
    install_requires=read_list('requirements.txt'),
    tests_require=read_list('requirements-dev.txt'),
    entry_points={
        'console_scripts': [
            'speechmatics = speechmatics.cli:main'
        ]
    },
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3"
    ],
    include_package_data=True,
)
