import speechmatics.models as models


def test_del_none():
    test_dict = {"a": None, "b": "stuff", "c": 0, "d": None, "e": False}
    got = models.del_none(test_dict)
    want = {"b": "stuff", "c": 0, "e": False}
    assert got == want


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
