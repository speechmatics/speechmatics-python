"""
Module with models used by speechmatics
"""
import ssl
from dataclasses import asdict, dataclass, field
from enum import Enum


def del_none(dictionary):
    for key, value in list(dictionary.items()):
        if value is None:
            del dictionary[key]
        elif isinstance(value, dict):
            del_none(value)
    return dictionary

# pylint: disable=R0902
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
            return {'type': 'file'}

        return {'type': 'raw',
                'encoding': self.encoding,
                'sample_rate': self.sample_rate}


@dataclass
class ConnectionSettings:
    url: str
    message_buffer_size: int = 512
    ssl_context: ssl.SSLContext = field(default_factory=ssl.create_default_context)
    semaphore_timeout_seconds: float = 120


class ClientMessageType(str, Enum):
    StartRecognition = 'StartRecognition'
    AddAudio = 'AddAudio'
    EndOfStream = 'EndOfStream'
    SetRecognitionConfig = 'SetRecognitionConfig'


class ServerMessageType(str, Enum):
    RecognitionStarted = 'RecognitionStarted'
    AudioAdded = 'AudioAdded'
    AddPartialTranscript = 'AddPartialTranscript'
    AddTranscript = 'AddTranscript'
    EndOfTranscript = 'EndOfTranscript'
    Info = 'Info'
    Warning = 'Warning'
    Error = 'Error'
