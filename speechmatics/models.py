# (c) 2020, Cantab Research Ltd.
"""
Data models and message types used by the library.
"""

import json
import ssl
import sys
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Any, Dict, List, Optional

from speechmatics.config import CONFIG_PATH, read_config_from_home
from speechmatics.constants import BATCH_SELF_SERVICE_URL, RT_SELF_SERVICE_URL

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover


SummaryContentType = Literal["informative", "conversational", "auto"]
SummaryLength = Literal["brief", "detailed"]
SummaryType = Literal["paragraphs", "bullets"]


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

    contents: List[str] = None
    """
    Specifies a list of items to be attached to the notification message.
    When multiple items are requested, they are included as named file
    attachments.
    """

    method: str = "post"
    """The HTTP(S) method to be used. Only `post` and `put` are supported."""

    auth_headers: List[str] = None
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

    audio_filtering_config: Optional[dict] = None
    """Configuration for limiting the transcription of quiet audio."""

    transcript_filtering_config: Optional[dict] = None
    """Configuration for applying filtering to the transcription."""


@dataclass
class RTSpeakerDiarizationConfig:
    """Real-time mode: Speaker diarization config."""

    max_speakers: int = None
    """This enforces the maximum number of speakers allowed in a single audio stream."""


@dataclass
class TranslationConfig:
    """Translation config."""

    target_languages: List[str] = None
    """Target languages for which translation should be produced."""

    def asdict(self):
        return asdict(self)


@dataclass
class RTTranslationConfig(TranslationConfig):
    """Real-time mode: Translation config."""

    enable_partials: bool = False
    """Indicates if partial translation, where sentences are produced
    immediately, is enabled."""


@dataclass
class BatchSpeakerDiarizationConfig:
    """Batch mode: Speaker diarization config."""

    speaker_sensitivity: float = None
    """The sensitivity of the speaker detection.
    This is a number between 0 and 1, where 0 means least sensitive and 1 means
    most sensitive."""


@dataclass
class BatchTranslationConfig(TranslationConfig):
    """Batch mode: Translation config."""


@dataclass
class BatchLanguageIdentificationConfig:
    """Batch mode: Language identification config."""

    expected_languages: Optional[List[str]] = None
    """Expected languages for language identification"""


@dataclass
class SummarizationConfig:
    """Defines summarization parameters."""

    content_type: SummaryContentType = "auto"
    """Optional summarization content_type parameter."""

    summary_length: SummaryLength = "brief"
    """Optional summarization summary_length parameter."""

    summary_type: SummaryType = "bullets"
    """Optional summarization summary_type parameter."""


@dataclass
class SentimentAnalysisConfig:
    """Sentiment Analysis config."""


@dataclass
class TopicDetectionConfig:
    """Defines topic detection parameters."""

    topics: Optional[List[str]] = None
    """Optional list of topics for topic detection."""


@dataclass
class AutoChaptersConfig:
    """Auto Chapters config."""


@dataclass
class AudioEventsConfig:
    types: Optional[List[str]] = None
    """Optional list of audio event types to detect."""

    def asdict(self):
        if self.types is None:
            return {}
        return asdict(self)


@dataclass(init=False)
class TranscriptionConfig(_TranscriptionConfig):
    # pylint: disable=too-many-instance-attributes
    """
    Real-time: Defines transcription parameters.
    The `.as_config()` method removes translation_config and returns it wrapped into a Speechmatics json config.
    """

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

    streaming_mode: bool = None
    """Indicates if we run the engine in streaming mode, or regular RT mode."""

    ctrl: dict = None
    """Internal Speechmatics flag that allows to give special commands to the engine."""

    enable_partials: bool = None
    """Indicates if partials for both transcripts and translation, where words are produced
    immediately, is enabled."""

    enable_transcription_partials: bool = None
    """Indicates if partial transcripts, where words are produced
    immediately, is enabled."""

    enable_translation_partials: bool = None
    """Indicates if partial translation, where words are produced
    immediately, is enabled."""

    translation_config: Optional[TranslationConfig] = None
    """Optional configuration for translation."""

    audio_events_config: Optional[AudioEventsConfig] = None
    """Optional configuration for audio events"""

    def as_config(self):
        dictionary = self.asdict()
        dictionary.pop("translation_config", None)
        dictionary.pop("audio_events_config", None)
        dictionary.pop("enable_translation_partials", None)
        enable_transcription_partials = dictionary.pop(
            "enable_transcription_partials", False
        )
        # set enable_partials to True if either one is True
        if dictionary.get("enable_partials") is True or enable_transcription_partials:
            dictionary["enable_partials"] = True

        return dictionary


@dataclass(init=False)
class BatchTranscriptionConfig(_TranscriptionConfig):
    # pylint: disable=too-many-instance-attributes
    """Batch: Defines transcription parameters for batch requests.
    The `.as_config()` method will return it wrapped into a Speechmatics json config."""

    fetch_data: FetchData = None
    """Optional configuration for fetching file for transcription."""

    notification_config: NotificationConfig = None
    """Optional configuration for callback notification."""

    language_identification_config: BatchLanguageIdentificationConfig = None
    """Optional configuration for language identification."""

    translation_config: TranslationConfig = None
    """Optional configuration for translation."""

    srt_overrides: SRTOverrides = None
    """Optional configuration for SRT output."""

    speaker_diarization_config: BatchSpeakerDiarizationConfig = None
    """The sensitivity of the speaker detection."""

    channel_diarization_labels: List[str] = None
    """Add your own speaker or channel labels to the transcript"""

    summarization_config: SummarizationConfig = None
    """Optional configuration for transcript summarization."""

    sentiment_analysis_config: Optional[SentimentAnalysisConfig] = None
    """Optional configuration for sentiment analysis of the transcript"""

    topic_detection_config: Optional[TopicDetectionConfig] = None
    """Optional configuration for detecting topics of the transcript"""

    auto_chapters_config: Optional[AutoChaptersConfig] = None
    """Optional configuration for detecting chapters of the transcript"""

    audio_events_config: Optional[AudioEventsConfig] = None

    def as_config(self):
        dictionary = self.asdict()

        fetch_data = dictionary.pop("fetch_data", None)
        notification_config = dictionary.pop("notification_config", None)
        language_identification_config = dictionary.pop(
            "language_identification_config", None
        )
        translation_config = dictionary.pop("translation_config", None)
        srt_overrides = dictionary.pop("srt_overrides", None)
        summarization_config = dictionary.pop("summarization_config", None)
        sentiment_analysis_config = dictionary.pop("sentiment_analysis_config", None)
        topic_detection_config = dictionary.pop("topic_detection_config", None)
        auto_chapters_config = dictionary.pop("auto_chapters_config", None)
        audio_events_config = dictionary.pop("audio_events_config", None)
        config = {"type": "transcription", "transcription_config": dictionary}

        if fetch_data:
            config["fetch_data"] = fetch_data

        if notification_config:
            if isinstance(notification_config, dict):
                notification_config = [notification_config]
            config["notification_config"] = notification_config

        if language_identification_config:
            config["language_identification_config"] = language_identification_config

        if translation_config:
            config["translation_config"] = translation_config

        if srt_overrides:
            config["output_config"] = {"srt_overrides": srt_overrides}

        if summarization_config:
            config["summarization_config"] = summarization_config

        if sentiment_analysis_config is not None:
            config["sentiment_analysis_config"] = sentiment_analysis_config

        if topic_detection_config:
            config["topic_detection_config"] = topic_detection_config

        if auto_chapters_config is not None:
            config["auto_chapters_config"] = auto_chapters_config

        if audio_events_config is not None:
            config["audio_events_config"] = audio_events_config

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


class UsageMode(str, Enum):
    # pylint: disable=invalid-name
    Batch = "batch"
    RealTime = "rt"


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

    auth_token: Optional[str] = None
    """auth token to authenticate a customer."""

    generate_temp_token: Optional[bool] = False
    """Automatically generate a temporary token for authentication.
    Enterprise customers should set this to False."""

    def set_missing_values_from_config(self, mode: UsageMode):
        stored_config = read_config_from_home()
        if self.url is None or self.url == "":
            url_key = "realtime_url" if mode == UsageMode.RealTime else "batch_url"
            if stored_config and url_key in stored_config:
                self.url = stored_config[url_key]
            else:
                raise ValueError(f"No URL provided or set in {CONFIG_PATH}")
        if self.auth_token is None or self.auth_token == "":
            if stored_config and stored_config.get("auth_token"):
                self.auth_token = stored_config["auth_token"]

    @classmethod
    def create(cls, mode: UsageMode, auth_token: Optional[str] = None):
        stored_config = read_config_from_home()
        default_url = (
            RT_SELF_SERVICE_URL
            if mode == UsageMode.RealTime
            else BATCH_SELF_SERVICE_URL
        )
        url_key = "realtime_url" if mode == UsageMode.RealTime else "batch_url"
        if stored_config and url_key in stored_config:
            url = stored_config[url_key]
        else:
            url = default_url
        if auth_token is not None:
            return ConnectionSettings(
                url=url,
                auth_token=auth_token,
                generate_temp_token=True,
            )
        if stored_config and stored_config.get("auth_token"):
            url = stored_config.get(url_key, default_url)
            return ConnectionSettings(
                url,
                auth_token=stored_config["auth_token"],
                generate_temp_token=stored_config.get("generate_temp_token", True),
            )
        raise ValueError(f"No acces token provided or set in {CONFIG_PATH}")


@dataclass
class RTConnectionSettings(ConnectionSettings):
    url = f"{RT_SELF_SERVICE_URL}/en"


@dataclass
class BatchConnectionSettings(ConnectionSettings):
    url = BATCH_SELF_SERVICE_URL


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

    AudioEventStarted = "AudioEventStarted"
    """Indicates the start of an audio event."""

    AudioEventEnded = "AudioEventEnded"
    """Indicates the end of an audio event."""

    AddPartialTranslation = "AddPartialTranslation"
    """Indicates a partial translation, which is an incomplete translation that
    is immediately produced and may change as more context becomes available.
    """

    AddTranslation = "AddTranslation"
    """Indicates the final translation of a part of the audio."""

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
