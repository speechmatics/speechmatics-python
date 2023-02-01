# (c) 2020, Cantab Research Ltd.
"""
Exceptions and errors used by the library.
"""


# Constants to hold valid error types for Connection Close errors
CONN_CLOSE_ERR_TYPES = [
    "protocol_error",
    "not_authorised",
    "not_allowed",
    "invalid_model",
    "quota_exceeded",
    "timelimit_exceeded",
    "job_error",
    "internal_error",
]


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
