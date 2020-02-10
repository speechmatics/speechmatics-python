# (c) 2020, Cantab Research Ltd.
"""
Data models and message types used by the library.
"""

import ssl

from dataclasses import asdict, dataclass, field
from enum import Enum

from speechmatics.helpers import del_none


# pylint: disable=too-many-instance-attributes
@dataclass
class TranscriptionConfig:
    """Defines transcription parameters."""

    language: str
    """ISO 639-1 language code. eg. ``en``"""

    output_locale: str = None
    """RFC-5646 language code for transcript output. eg. ``en-AU``"""

    additional_vocab: dict = None
    """Additional vocabulary that is not part of the standard language."""

    diarization: str = None
    """Indicates type of diarization to use, if any."""

    max_delay: float = None
    """Maximum acceptable delay."""

    speaker_change_sensitivity: float = None
    """Sensitivity level for speaker change."""

    enable_partials: bool = None
    """Indicates if partial transcription, where words are produced
    immediately, is enabled. """

    punctuation_overrides: dict = None
    """Permitted puctuation marks for advanced punctuation."""

    n_best_limit: int = None
    """Specifies the number of best matches to be returned for an uttarance."""

    def asdict(self):
        dictionary = asdict(self)
        d_without_nones = del_none(dictionary)
        return d_without_nones


@dataclass
class AudioSettings:
    """Defines audio parameters."""

    encoding: str = None
    """Encoding format."""

    sample_rate: int = 44100
    """Sampling rate."""

    chunk_size: int = 1024 * 4
    """Chunk size."""

    def asdict(self):
        if not self.encoding:
            return {"type": "file"}

        return {
            "type": "raw",
            "encoding": self.encoding,
            "sample_rate": self.sample_rate,
        }


@dataclass
class ConnectionSettings:
    """Defines connection parameters."""

    url: str
    """Websocket server endpoint."""

    message_buffer_size: int = 512
    """Message buffer size in bytes."""

    ssl_context: ssl.SSLContext = field(
        default_factory=ssl.create_default_context)
    """SSL context."""

    semaphore_timeout_seconds: float = 120
    """Semaphore timeout in seconds."""


class ClientMessageType(str, Enum):
    """Defines various messages sent from client to server."""

    StartRecognition = "StartRecognition"
    """Initiates a recognition job based on configuration set previously."""

    AddAudio = "AddAudio"
    """Adds more audio data to the recognition job."""

    EndOfStream = "EndOfStream"
    """Indicates the end of audio stream and that the client has send all audio
    it intends to send."""

    SetRecognitionConfig = "SetRecognitionConfig"
    """Allows job configuration to be set after the initial `StartRecognition`
    message."""


class ServerMessageType(str, Enum):
    """Defines various message types sent from server to client."""

    RecognitionStarted = "RecognitionStarted"
    """Indicates that recognition has started."""

    AudioAdded = "AudioAdded"
    """Indicates an acknowledgement that the server has added the audio."""

    AddPartialTranscript = "AddPartialTranscript"
    """Indicates a partial transcript, which is portion of the transcript that
    is immediately produced but may change as more context becomes available.
    """

    AddTranscript = "AddTranscript"
    """Indicates a full transcript that represents a sentence."""

    EndOfTranscript = "EndOfTranscript"
    """Indicates that all audio has been processed and that client can safely
    disconnect."""

    Info = "Info"
    """Indicates a generic info message."""

    Warning = "Warning"
    """Indicates a generic warning message."""

    Error = "Error"
    """Indicates n generic error message."""
