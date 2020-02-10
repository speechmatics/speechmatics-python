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
    language: str
    output_locale: str = None
    additional_vocab: dict = None
    diarization: str = None
    max_delay: float = None
    speaker_change_sensitivity: float = None
    enable_partials: bool = None
    punctuation_overrides: dict = None
    n_best_limit: int = None

    def asdict(self):
        dictionary = asdict(self)
        d_without_nones = del_none(dictionary)
        return d_without_nones


@dataclass
class AudioSettings:
    encoding: str = None
    sample_rate: int = 44100
    chunk_size: int = 1024 * 4

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
    url: str
    message_buffer_size: int = 512
    ssl_context: ssl.SSLContext = field(
        default_factory=ssl.create_default_context)
    semaphore_timeout_seconds: float = 120


class ClientMessageType(str, Enum):
    StartRecognition = "StartRecognition"
    AddAudio = "AddAudio"
    EndOfStream = "EndOfStream"
    SetRecognitionConfig = "SetRecognitionConfig"


class ServerMessageType(str, Enum):
    """Defines various message types returned by the server"""

    """Indicates that recognition has started"""
    RecognitionStarted = "RecognitionStarted"

    """Indicates an acknowledgement that the server has added the audio"""
    AudioAdded = "AudioAdded"

    AddPartialTranscript = "AddPartialTranscript"
    AddTranscript = "AddTranscript"
    EndOfTranscript = "EndOfTranscript"
    Info = "Info"
    Warning = "Warning"
    Error = "Error"
