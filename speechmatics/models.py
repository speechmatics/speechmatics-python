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
    """ISO 639-1 language code. eg. `en`"""

    operating_point: str = None
    """Specifies which acoustic model to use."""

    output_locale: str = None
    """RFC-5646 language code for transcript output. eg. `en-AU`"""

    additional_vocab: dict = None
    """Additional vocabulary that is not part of the standard language."""

    diarization: str = None
    """Indicates type of diarization to use, if any."""

    max_delay: float = None
    """Maximum acceptable delay."""

    max_delay_mode: str = None
    """Determines whether the threshold specified in max_delay can be exceeded
    if a potential entity is detected. Flexible means if a potential entity
    is detected, then the max_delay can be overriden until the end of that
    entity. Fixed means that max_delay specified ignores any potential
    entity that would not be completed within that threshold."""

    speaker_change_sensitivity: float = None
    """Sensitivity level for speaker change."""

    enable_partials: bool = None
    """Indicates if partial transcription, where words are produced
    immediately, is enabled. """

    enable_entities: bool = None
    """Indicates if inverse text normalization entity output is enabled."""

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
    """Encoding format when raw audio is used. Allowed values are
    `pcm_f32le`, `pcm_s16le` and `mulaw`."""

    sample_rate: int = 44100
    """Sampling rate in hertz."""

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

    ping_timeout_seconds: float = 60
    """Ping-pong timeout in seconds."""

    auth_token: str = None
    """auth token to authenticate a customer.
    This auth token is only applicable for RT-SaaS."""


class ClientMessageType(str, Enum):
    """Defines various messages sent from client to server."""

    StartRecognition = "StartRecognition"
    """Initiates a recognition job based on configuration set previously."""

    AddAudio = "AddAudio"
    """Adds more audio data to the recognition job. The server confirms
    receipt by sending an :py:attr:`ServerMessageType.AudioAdded` message."""

    EndOfStream = "EndOfStream"
    """Indicates that the client has no more audio to send."""

    SetRecognitionConfig = "SetRecognitionConfig"
    """Allows the client to re-configure the recognition session."""


class ServerMessageType(str, Enum):
    """Defines various message types sent from server to client."""

    RecognitionStarted = "RecognitionStarted"
    """Server response to :py:attr:`ClientMessageType.StartRecognition`,
    acknowledging that a recognition session has started."""

    AudioAdded = "AudioAdded"
    """Server response to :py:attr:`ClientMessageType.AddAudio`, indicating
    that audio has been added successfully."""

    AddPartialTranscript = "AddPartialTranscript"
    """Indicates a partial transcript, which is an incomplete transcript that
    is immediately produced and may change as more context becomes available.
    """

    AddTranscript = "AddTranscript"
    """Indicates the final transcript of a part of the audio."""

    EndOfTranscript = "EndOfTranscript"
    """Server response to :py:attr:`ClientMessageType.EndOfStream`,
    after the server has finished sending all :py:attr:`AddTranscript`
    messages."""

    Info = "Info"
    """Indicates a generic info message."""

    Warning = "Warning"
    """Indicates a generic warning message."""

    Error = "Error"
    """Indicates n generic error message."""
