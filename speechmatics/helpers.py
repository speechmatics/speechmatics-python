# (c) 2020, Cantab Research Ltd.
"""
Helper functions used by the library.
"""

import asyncio
import concurrent.futures
import inspect
import json
import os
import sys

import pkg_resources


def del_none(dictionary):
    """
    Recursively delete from the dictionary all entries which values are None.
    This function changes the input parameter in place.

    :param dictionary: input dictionary
    :type dictionary: dict

    :return: output dictionary
    :rtype: dict
    """
    for key, value in list(dictionary.items()):
        if value is None:
            del dictionary[key]
        elif isinstance(value, dict):
            del_none(value)
    return dictionary


def json_utf8(func):
    """A decorator to turn a function's return value into JSON"""

    def wrapper(*args, **kwargs):
        """wrapper"""
        return json.dumps(func(*args, **kwargs))

    return wrapper


async def read_in_chunks(stream, chunk_size):
    """
    Utility method for reading in and yielding chunks

    :param stream: file-like object to read audio from
    :type stream: io.IOBase

    :param chunk_size: maximum chunk size in bytes
    :type chunk_size: int

    :raises ValueError: if no data was read from the stream

    :return: a sequence of chunks of data where the length in bytes of each
        chunk is <= max_sample_size and a multiple of max_sample_size
    :rtype: collections.AsyncIterable

    """
    while True:
        # Work with both async and synchronous file readers.
        if inspect.iscoroutinefunction(stream.read):
            audio_chunk = await stream.read(chunk_size)
        else:
            # Run the read() operation in a separate thread to avoid blocking the event loop.
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_chunk = await asyncio.get_event_loop().run_in_executor(
                    executor, stream.read, chunk_size
                )

        if not audio_chunk:
            break
        yield audio_chunk


def get_version() -> str:
    """
    Reads the version number from the package or from VERSION file in case
    the package information is not found.

    :return: the library version
    :rtype: str
    """
    try:
        version = pkg_resources.get_distribution("speechmatics-python").version
    except pkg_resources.DistributionNotFound:
        # The library is not running from the distributed package
        # Get the version from the VERSION file
        base_path = os.path.abspath(os.path.dirname(__file__))
        version_path = os.path.join(base_path, "..", "VERSION")
        with open(version_path, "r", encoding="utf-8") as version_file:
            version = version_file.read().strip()

    return version


def _process_status_errors(error):
    """
    Takes an httpx.HTTPSStatusError and prints in a useful format for CLI

    :param error: the status error produced by the server for a request
    :type error: httpx.HTTPStatusError

    :raises SystemExit: for all cases
    """

    error_string = f"{error.request.method} request to {error.request.url} returned {error.response.status_code}"
    if error.response.status_code == 401:
        sys.exit(
            f"Unauthorized: {error_string}. \n Make sure you're using a valid API key or JWT."
        )
    if error.response.status_code == 404:
        sys.exit(
            f"NotFound: {error_string}. Make sure the url and resource id are correct."
        )
    if error.response.status_code == 429:
        sys.exit(
            f"TooManyRequests: {error_string}. "
            + "In order to ensure a good service to all our users, we rate limit requests. "
            + "Consider redesigning your code to reduce the number of requests or spread your requests over time."
        )
    if error.response.status_code in [400, 422]:
        sys.exit(
            f"BadOrUnprocessableRequest: {error_string}.\n\nresponse: {error.response.text}\n"
            + "Make sure the config you've submitted has a valid structure, and that the values are allowed.\n"
            + "(e.g. --lang abc is invalid)."
        )
    sys.exit(f"httpx.HTTPStatusError: {error}")
