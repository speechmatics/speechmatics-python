# (c) 2020, Cantab Research Ltd.
"""
Data models and message types used by the library.
"""

import json
import ssl

from dataclasses import asdict, dataclass, field, fields
from enum import Enum

from typing import Any, Dict, List, Optional


@dataclass
class FetchData:
    """Batch: Optional configuration for fetching file for transcription."""

    url: str
    """URL to fetch"""

    auth_headers: str = None
    """
    A list of additional headers to be added to the input fetch request
    when using http or https. This is intended to support authentication or
    authorization, for example by supplying an OAuth2 bearer token
    """


@dataclass
class NotificationConfig:
    """Batch: Optional configuration for callback notification."""

    url: str
    """URL for notification. The `id` and `status` query parameters will be added."""

    contents: str = None
    """
    Specifies a list of items to be attached to the notification message.
    When multiple items are requested, they are included as named file
    attachments.
    """

    method: str = "post"
    """The HTTP(S) method to be used. Only `post` and `put` are supported."""

    auth_headers: str = None
    """
    A list of additional headers to be added to the notification request
    when using http or https. This is intended to support authentication or
    authorization, for example by supplying an OAuth2 bearer token
    """


@dataclass
class SRTOverrides:
    """Batch: Optional configuration for SRT output."""

    max_line_length: int = 37
    """Maximum count of characters per subtitle line including white space"""

    max_lines: int = 2
    """Sets maximum count of lines in a subtitle section"""


@dataclass
class _TranscriptionConfig:  # pylint: disable=too-many-instance-attributes
    """Base model for defining transcription parameters."""

    def __init__(self, language=None, **kwargs):
        """
        Ignores values which are not dataclass members when initalising.
        This allows **kwargs to contain fields which are not in the model,
        which is useful for reusing code to build RT and batch configs.
        See cli.get_transcription_config() for an example.
        """
        super().__init__()
        # the language attribute is a special case, as it's a positional parameter
        if language is not None:
            self.language = language

        # pylint: disable=consider-using-set-comprehension
        names = set([f.name for f in fields(self)])
        for key, value in kwargs.items():
            if key in names:
                setattr(self, key, value)

    def asdict(self) -> Dict[Any, Any]:
        """Returns model as a dict while excluding None values recursively."""
        return asdict(
            self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None}
        )

    language: str = "en"
    """ISO 639-1 language code. eg. `en`"""

    operating_point: str = None
    """Specifies which acoustic model to use."""

    output_locale: str = None
    """RFC-5646 language code for transcript output. eg. `en-AU`"""

    diarization: str = None
    """Indicates type of diarization to use, if any."""

    additional_vocab: dict = None
    """Additional vocabulary that is not part of the standard language."""

    punctuation_overrides: dict = None
    """Permitted puctuation marks for advanced punctuation."""

    domain: str = None
    """Optionally request a language pack optimized for a specific domain,
    e.g. 'finance'"""

    enable_entities: bool = None
    """Indicates if inverse text normalization entity output is enabled."""


@dataclass
class RTSpeakerDiarizationConfig:
    """Real-time mode: Speaker diarization config."""

    max_speakers: int = None
    """This enforces the maximum number of speakers allowed in a single audio stream."""


@dataclass
class BatchSpeakerDiarizationConfig:
    """Batch mode: Speaker diarization config."""

    speaker_sensitivity: int = None
    """The sensitivity of the speaker detection."""


@dataclass
class BatchTranslationConfig:
    """Batch mode: Translation config."""

    target_languages: List[str] = None
    """Target languages for which translation should be produced"""


@dataclass(init=False)
class TranscriptionConfig(_TranscriptionConfig):
    """Real-time: Defines transcription parameters."""

    max_delay: float = None
    """Maximum acceptable delay."""

    max_delay_mode: str = None
    """Determines whether the threshold specified in max_delay can be exceeded
    if a potential entity is detected. Flexible means if a potential entity
    is detected, then the max_delay can be overriden until the end of that
    entity. Fixed means that max_delay specified ignores any potential
    entity that would not be completed within that threshold."""

    speaker_diarization_config: RTSpeakerDiarizationConfig = None
    """Configuration for speaker diarization."""

    speaker_change_sensitivity: float = None
    """Sensitivity level for speaker change."""

    enable_partials: bool = None
    """Indicates if partial transcription, where words are produced
    immediately, is enabled. """


@dataclass(init=False)
class BatchTranscriptionConfig(_TranscriptionConfig):
    """Batch: Defines transcription parameters for batch requests.
    The `.as_config()` method will return it wrapped into a Speechmatics json config."""

    fetch_data: FetchData = None
    """Optional configuration for fetching file for transcription."""

    notification_config: NotificationConfig = None
    """Optional configuration for callback notification."""

    translation_config: BatchTranslationConfig = None
    """Optional configuration for translation."""

    srt_overrides: SRTOverrides = None
    """Optional configuration for SRT output."""

    speaker_diarization_config: BatchSpeakerDiarizationConfig = None
    """The sensitivity of the speaker detection."""

    channel_diarization_labels: List[str] = None
    """Add your own speaker or channel labels to the transcript"""

    def as_config(self):
        dictionary = self.asdict()

        fetch_data = dictionary.pop("fetch_data", None)
        notification_config = dictionary.pop("notification_config", None)
        translation_config = dictionary.pop("translation_config", None)
        srt_overrides = dictionary.pop("srt_overrides", None)

        config = {"type": "transcription", "transcription_config": dictionary}

        if fetch_data:
            config["fetch_data"] = fetch_data

        if notification_config:
            if isinstance(notification_config, dict):
                notification_config = [notification_config]
            config["notification_config"] = notification_config

        if translation_config:
            config["translation_config"] = translation_config

        if srt_overrides:
            config["output_config"] = {"srt_overrides": srt_overrides}

        return json.dumps(config)


@dataclass
class AudioSettings:
    """Real-time: Defines audio parameters."""

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

    ssl_context: ssl.SSLContext = field(default_factory=ssl.create_default_context)
    """SSL context."""

    semaphore_timeout_seconds: float = 120
    """Semaphore timeout in seconds."""

    ping_timeout_seconds: float = 60
    """Ping-pong timeout in seconds."""

    auth_token: str = None
    """auth token to authenticate a customer.
    This auth token is only applicable for RT-SaaS."""

    generate_temp_token: Optional[bool] = False
    """Automatically generate a temporary token for authentication.
    Non-enterprise customers must set this to True. Enterprise customers should set this to False."""


class ClientMessageType(str, Enum):
    # pylint: disable=invalid-name
    """Real-time: Defines various messages sent from client to server."""

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
    # pylint: disable=invalid-name
    """Real-time: Defines various message types sent from server to client."""

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
