import pytest

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
    config_dict = config.asdict()
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


@pytest.mark.parametrize(
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
