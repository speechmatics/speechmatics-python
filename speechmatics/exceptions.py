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
