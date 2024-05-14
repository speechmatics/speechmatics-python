from dataclasses import asdict

from pytest import mark, param

from speechmatics import models
from speechmatics.batch_client import BatchClient


def test_audio_settings_asdict_when_encoding_none():
    audio_settings = models.AudioSettings()
    audio_settings.encoding = None
    got = audio_settings.asdict()
    want = {"type": "file"}
    assert got == want


def test_audio_settings_asdict_when_encoding_set():
    audio_settings = models.AudioSettings()
    audio_settings.encoding = "pcm_f32le"
    got = audio_settings.asdict()
    want = {
        "type": "raw",
        "encoding": audio_settings.encoding,
        "sample_rate": audio_settings.sample_rate,
    }
    assert got == want


def test_transcriptionconfig_excludes_nones():
    config = models.TranscriptionConfig()
    config_dict = config.as_config()
    assert None not in config_dict.values()


def test_transcriptionconfig_positional_arg():
    config = models.TranscriptionConfig("de")
    assert config.language == "de"


def test_batchtranscriptionconfig_excludes_nones():
    config = models.BatchTranscriptionConfig()
    config_dict = config.asdict()
    assert None not in config_dict.values()


def test_batchtranscriptionconfig_json_simple():
    config = models.BatchTranscriptionConfig()
    got = config.as_config()
    want = '{"type": "transcription", "transcription_config": {"language": "en"}}'
    assert got == want


def test_translationconfig_default_values():
    config = models.RTTranslationConfig()
    assert {"target_languages": None, "enable_partials": False} == config.asdict()


@mark.parametrize(
    "target_languages, enable_partials, want_config",
    [
        (["fr"], False, {"target_languages": ["fr"], "enable_partials": False}),
        (["fr"], True, {"target_languages": ["fr"], "enable_partials": True}),
        (
            ["fr", "es"],
            True,
            {"target_languages": ["fr", "es"], "enable_partials": True},
        ),
    ],
)
def test_translationconfig(target_languages, enable_partials, want_config):
    config = models.RTTranslationConfig(
        target_languages=target_languages, enable_partials=enable_partials
    )
    assert want_config == config.asdict()


@mark.parametrize(
    "url, want",
    [
        ("example.com/v2", "example.com/v2"),
        ("example.com/v2/", "example.com/v2"),
        ("example.com/", "example.com/v2"),
        ("example.com", "example.com/v2"),
    ],
)
def test_connection_settings_url(url, want):
    connection_settings = models.ConnectionSettings(url=url)
    batch_client = BatchClient(connection_settings)
    got = batch_client.connection_settings.url
    assert got == want


@mark.parametrize(
    "params, want",
    [
        param(
            {},
            {
                "content_type": "auto",
                "summary_length": "brief",
                "summary_type": "bullets",
            },
            id="default params",
        ),
        param(
            {"content_type": "informative"},
            {
                "content_type": "informative",
                "summary_length": "brief",
                "summary_type": "bullets",
            },
            id="set content_type param",
        ),
        param(
            {"summary_length": "detailed"},
            {
                "content_type": "auto",
                "summary_length": "detailed",
                "summary_type": "bullets",
            },
            id="set summary_length param",
        ),
        param(
            {"summary_type": "paragraphs"},
            {
                "content_type": "auto",
                "summary_length": "brief",
                "summary_type": "paragraphs",
            },
            id="set summary_type param",
        ),
        param(
            {
                "content_type": "auto",
                "summary_length": "brief",
                "summary_type": "bullets",
            },
            {
                "content_type": "auto",
                "summary_length": "brief",
                "summary_type": "bullets",
            },
            id="set all params",
        ),
    ],
)
def test_summarization_config(params, want):
    summarization_config = models.SummarizationConfig(**params)
    assert asdict(summarization_config) == want


@mark.parametrize(
    "params, want",
    [
        param(
            {},
            {"topics": None},
            id="default params",
        ),
        param(
            {"topics": ["topic1", "topic2"]},
            {"topics": ["topic1", "topic2"]},
            id="set topics param",
        ),
    ],
)
def test_topic_detection_config(params, want):
    topic_detection_config = models.TopicDetectionConfig(**params)
    assert asdict(topic_detection_config) == want


@mark.parametrize(
    "params, want",
    [
        param(
            {"url": "example.com"},
            {
                "url": "example.com",
                "contents": None,
                "method": "post",
                "auth_headers": None,
            },
        ),
        param(
            {
                "url": "example.com",
                "contents": ["transcript.txt"],
                "method": "put",
                "auth_headers": ["Authorization", "Bearer token"],
            },
            {
                "url": "example.com",
                "contents": ["transcript.txt"],
                "method": "put",
                "auth_headers": ["Authorization", "Bearer token"],
            },
        ),
    ],
)
def test_notification_config(params, want):
    notification_config = models.NotificationConfig(**params)
    assert asdict(notification_config) == want


@mark.parametrize(
    "params, want",
    [
        param(
            {"types": None},
            {},
            id="default params",
        ),
        param(
            {"types": ["music"]},
            {"types": ["music"]},
            id="set types param",
        ),
    ],
)
def test_audio_events_config_config(params, want):
    audio_events_config = models.AudioEventsConfig(**params)
    assert audio_events_config.asdict() == want
