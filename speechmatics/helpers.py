# (c) 2020, Cantab Research Ltd.
"""
Helper functions used by the library.
"""

import json
import inspect


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
    """ A decorator to turn a function's return value into JSON """

    def wrapper(*args, **kwargs):
        """ wrapper """
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
    count = 0
    while True:
        # Work with both async and synchronous file readers.
        if inspect.iscoroutinefunction(stream.read):
            audio_chunk = await stream.read(chunk_size)
        else:
            audio_chunk = stream.read(chunk_size)

        if not audio_chunk:
            break
        yield audio_chunk
        count += 1


def call_middleware(middlewares, event_name, *args):
    for middleware in middlewares[event_name]:
        middleware(*args)
