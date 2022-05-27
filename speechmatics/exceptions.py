# (c) 2020, Cantab Research Ltd.
"""
Exceptions and errors used by the library.
"""


class TranscriptionError(Exception):
    """
    Indicates an error in transcription.
    """


class EndOfTranscriptException(Exception):
    """
    Indicates that the transcription session has finished.
    """


class ForceEndSession(Exception):
    """
    Can be raised by the user from a middleware or event handler
    in order to force the transcription session to end early.
    """


class JobNotFoundException(Exception):
    """
    Indicates that job ID was not found.
    """
