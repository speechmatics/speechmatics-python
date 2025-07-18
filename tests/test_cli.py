import argparse
import collections
import logging
from math import ceil
import os

import pytest
import toml

from speechmatics import cli, cli_parser
from speechmatics.constants import (
    BATCH_SELF_SERVICE_URL,
    RT_SELF_SERVICE_URL,
)
from tests.utils import path_to_test_resource


@pytest.mark.parametrize(
    "args, values",
    [
        (
            ["rt", "transcribe"],
            {
                "mode": "rt",
                "command": "transcribe",
                "ssl_mode": "regular",
                "punctuation_permitted_marks": None,
                "enable_partials": False,
            },
        ),
        (
            ["batch", "transcribe"],
            {
                "mode": "batch",
                "command": "transcribe",
                "ssl_mode": "regular",
                "punctuation_permitted_marks": None,
                "output_format": "txt",
            },
        ),
        (["-v", "rt", "transcribe"], {"verbose": 1}),
        (["-vv", "batch", "transcribe"], {"verbose": 2}),
        (
            ["rt", "transcribe", "--language", "fr"],
            {"language": "fr"},
        ),
        (
            ["batch", "transcribe", "--language", "fr"],
            {"language": "fr"},
        ),
        (
            ["rt", "transcribe", "--output-locale", "en-GB"],
            {"output_locale": "en-GB"},
        ),
        (
            ["batch", "transcribe", "--output-locale", "en-GB"],
            {"output_locale": "en-GB"},
        ),
        (
            ["rt", "transcribe", "--additional-vocab", "Speechmatics", "gnocchi"],
            {"additional_vocab": ["Speechmatics", "gnocchi"]},
        ),
        (
            [
                "rt",
                "transcribe",
                "--extra-headers",
                "magic_header=magic_value",
                "another_magic_header=another_magic_value",
            ],
            {
                "extra_headers": {
                    "magic_header": "magic_value",
                    "another_magic_header": "another_magic_value",
                }
            },
        ),
        (
            [
                "rt",
                "transcribe",
                "--multichannel",
                "test_channel_1,test_channel_2",
                "--diarization=speaker",
            ],
            {
                "mode": "rt",
                "command": "transcribe",
                "multichannel": "test_channel_1,test_channel_2",
                "diarization": "speaker",
            },
        ),
        (
            ["batch", "transcribe", "--additional-vocab", "Speechmatics", "gnocchi"],
            {"additional_vocab": ["Speechmatics", "gnocchi"]},
        ),
        (
            [
                "rt",
                "transcribe",
                "--additional-vocab",
                "gnocchi:nokey,nochi",
                "Speechmatics:speechmadticks",
            ],
            {
                "additional_vocab": [
                    {"content": "gnocchi", "sounds_like": ["nokey", "nochi"]},
                    {"content": "Speechmatics", "sounds_like": ["speechmadticks"]},
                ]
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--additional-vocab",
                "gnocchi:nokey,nochi",
                "Speechmatics:speechmadticks",
            ],
            {
                "additional_vocab": [
                    {"content": "gnocchi", "sounds_like": ["nokey", "nochi"]},
                    {"content": "Speechmatics", "sounds_like": ["speechmadticks"]},
                ]
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--replacement-words",
                "foo:bar",
                "/regex*/:[redacted]",
            ],
            {
                "replacement_words": [
                    {"from": "foo", "to": "bar"},
                    {"from": "/regex*/", "to": "[redacted]"},
                ],
            },
        ),
        (
            [
                "rt",
                "transcribe",
                "--replacement-words",
                "foo:bar",
                "/regex*/:[redacted]",
            ],
            {
                "replacement_words": [
                    {"from": "foo", "to": "bar"},
                    {"from": "/regex*/", "to": "[redacted]"},
                ],
            },
        ),
        (
            ["rt", "transcribe", "--punctuation-permitted-marks", ", ? ."],
            {"punctuation_permitted_marks": ", ? ."},
        ),
        (
            ["batch", "transcribe", "--punctuation-permitted-marks", ", ? ."],
            {"punctuation_permitted_marks": ", ? ."},
        ),
        (
            ["rt", "transcribe", "--punctuation-permitted-marks", ""],
            {"punctuation_permitted_marks": ""},
        ),
        (
            ["batch", "transcribe", "--punctuation-permitted-marks", ""],
            {"punctuation_permitted_marks": ""},
        ),
        (
            ["rt", "transcribe", "--operating-point=standard"],
            {"operating_point": "standard"},
        ),
        (
            ["batch", "transcribe", "--operating-point=standard"],
            {"operating_point": "standard"},
        ),
        (
            ["rt", "transcribe", "--operating-point=enhanced"],
            {"operating_point": "enhanced"},
        ),
        (
            ["batch", "transcribe", "--operating-point=enhanced"],
            {"operating_point": "enhanced"},
        ),
        (["rt", "transcribe", "--ssl-mode=insecure"], {"ssl_mode": "insecure"}),
        (["rt", "transcribe", "--ssl-mode=none"], {"ssl_mode": "none"}),
        (["rt", "transcribe", "--enable-partials"], {"enable_partials": True}),
        (
            ["rt", "transcribe", "--enable-transcription-partials"],
            {"enable_transcription_partials": True},
        ),
        (
            ["rt", "transcribe", "--enable-translation-partials"],
            {"enable_translation_partials": True},
        ),
        (["rt", "transcribe", "--enable-entities"], {"enable_entities": True}),
        (
            ["rt", "transcribe", "--end-of-utterance-silence-trigger=1.8"],
            {"end_of_utterance_silence_trigger": 1.8},
        ),
        (["batch", "transcribe", "--enable-entities"], {"enable_entities": True}),
        (
            ["batch", "transcribe", "--diarization=speaker"],
            {
                "diarization": "speaker",
                "speaker_diarization_prefer_current_speaker": False,
                "speaker_diarization_sensitivity": None,
            },
        ),
        (
            ["batch", "transcribe", "--speaker-diarization-prefer-current-speaker"],
            {"speaker_diarization_prefer_current_speaker": True},
        ),
        (
            ["batch", "transcribe", "--speaker-diarization-sensitivity=0.7"],
            {"speaker_diarization_sensitivity": 0.7},
        ),
        (
            ["rt", "transcribe", "--diarization=speaker"],
            {
                "diarization": "speaker",
                "speaker_diarization_prefer_current_speaker": False,
                "speaker_diarization_max_speakers": None,
                "speaker_diarization_sensitivity": None,
            },
        ),
        (
            ["rt", "transcribe", "--speaker-diarization-max-speakers=3"],
            {"speaker_diarization_max_speakers": 3},
        ),
        (
            ["rt", "transcribe", "--speaker-diarization-prefer-current-speaker"],
            {"speaker_diarization_prefer_current_speaker": True},
        ),
        (
            ["rt", "transcribe", "--speaker-diarization-sensitivity=0.7"],
            {"speaker_diarization_sensitivity": 0.7},
        ),
        (
            [
                "batch",
                "transcribe",
                "--diarization=channel",
                "--channel-diarization-labels=label5 label4 label3",
            ],
            {
                "diarization": "channel",
                "channel_diarization_labels": ["label5 label4 label3"],
            },
        ),
        (["rt", "transcribe", "--auth-token=xyz"], {"auth_token": "xyz"}),
        (
            ["batch", "transcribe", "--domain=finance"],
            {"domain": "finance"},
        ),
        (
            ["rt", "transcribe", "--domain=finance"],
            {"domain": "finance"},
        ),
        (
            ["batch", "transcribe", "--output-format=json-v2"],
            {"output_format": "json-v2"},
        ),
        (["batch", "submit"], {"command": "submit"}),
        (
            ["rt", "transcribe", "--config-file=data/transcription_config.json"],
            {"config_file": "data/transcription_config.json"},
        ),
        (
            ["batch", "transcribe", "--translation-langs=de"],
            {
                "translation_target_languages": "de",
                "output_format": "txt",
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--output-format=json-v2",
                "--translation-langs=de,es,cs",
            ],
            {
                "translation_target_languages": "de,es,cs",
                "output_format": "json-v2",
            },
        ),
        (
            ["batch", "submit", "--translation-langs=de"],
            {
                "translation_target_languages": "de",
                "output_format": "txt",
            },
        ),
        (
            [
                "batch",
                "submit",
                "--output-format=json-v2",
                "--translation-langs=de,es,cs",
            ],
            {
                "translation_target_languages": "de,es,cs",
                "output_format": "json-v2",
            },
        ),
        (
            [
                "batch",
                "submit",
                "--langid-langs=de,es,cs",
            ],
            {
                "langid_expected_languages": "de,es,cs",
            },
        ),
        (
            ["batch", "transcribe", "--summarize"],
            {
                "summarize": True,
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--summarize",
                "--summary-content-type=informative",
            ],
            {
                "summarize": True,
                "content_type": "informative",
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--summarize",
                "--summary-content-type=informative",
            ],
            {
                "summarize": True,
                "content_type": "informative",
            },
        ),
        (
            ["batch", "transcribe", "--summarize", "--summary-length=detailed"],
            {
                "summarize": True,
                "summary_length": "detailed",
            },
        ),
        (
            ["batch", "transcribe", "--summarize", "--summary-type=paragraphs"],
            {
                "summarize": True,
                "summary_type": "paragraphs",
            },
        ),
        (
            ["batch", "transcribe", "--sentiment-analysis"],
            {
                "sentiment_analysis": True,
            },
        ),
        (
            ["batch", "transcribe", "--detect-topics"],
            {
                "detect_topics": True,
            },
        ),
        (
            [
                "batch",
                "transcribe",
                "--detect-topics",
                "--topics=topic1,topic2,topic3",
            ],
            {
                "detect_topics": True,
                "topics": "topic1,topic2,topic3",
            },
        ),
        (
            ["batch", "transcribe", "--detect-chapters"],
            {
                "detect_chapters": True,
            },
        ),
        (
            ["batch", "transcribe", "--volume-threshold", "3.1"],
            {"volume_threshold": 3.1},
        ),
        (
            ["batch", "transcribe", "--remove-disfluencies"],
            {"remove_disfluencies": True},
        ),
    ],
)
def test_cli_arg_parse_with_file(args, values):
    common_transcribe_args = ["--auth-token=xyz", "--url=example", "fake_file.wav"]
    if "--multichannel" in args:
        common_transcribe_args.append("very_fake_file.wav")
    test_args = args + common_transcribe_args
    actual_values = vars(cli.parse_args(args=test_args))

    for key, val in values.items():
        assert key in actual_values, f"Expected {key} in {actual_values}"
        assert actual_values[key] == val, f"Expected {actual_values} to match {values}"


@pytest.mark.parametrize(
    "args, values",
    [
        (
            ["transcribe", "--url", "ws://127.0.0.1"],
            {"mode": "rt", "command": "transcribe"},
        ),
        (
            ["transcribe", "--url", "wss://127.0.0.1:9000"],
            {"mode": "rt", "command": "transcribe"},
        ),
    ],
)
def test_cli_arg_parse_transcribe_url(args, values):
    connection_args = ["--auth-token=xyz"]
    test_args = args + connection_args + ["fake_file.wav"]
    actual_values = vars(cli.parse_args(args=test_args))

    for key, val in values.items():
        assert actual_values[key] == val


@pytest.mark.parametrize(
    "args, values",
    [
        (
            ["batch", "list-jobs"],
            {"mode": "batch", "command": "list-jobs"},
        ),
        (
            ["batch", "get-results", "--job-id=abc123"],
            {"mode": "batch", "command": "get-results", "job_id": "abc123"},
        ),
        (
            ["batch", "get-results", "--job-id=abc123", "--output-format=srt"],
            {"output_format": "srt"},
        ),
        (
            ["batch", "delete", "--job-id=abc123"],
            {"mode": "batch", "command": "delete", "job_id": "abc123"},
        ),
        (
            ["batch", "delete", "--job-id=abc123", "--force"],
            {
                "mode": "batch",
                "command": "delete",
                "job_id": "abc123",
                "force_delete": True,
            },
        ),
        (
            ["batch", "job-status", "--job-id=abc123"],
            {"mode": "batch", "command": "job-status", "job_id": "abc123"},
        ),
    ],
)
def test_cli_list_arg_parse_without_file(args, values):
    required_args = ["--url=example", "--auth-token=xyz"]
    test_args = args + required_args
    actual_values = vars(cli.parse_args(args=test_args))

    for key, val in values.items():
        assert actual_values[key] == val


def test_parse_additional_vocab(tmp_path, mocker):
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text('["Speechmatics", "gnocchi"]')
    assert cli.parse_additional_vocab(vocab_file) == (["Speechmatics", "gnocchi"])

    vocab_file.write_text('[{"content": "gnocchi", "sounds_like": ["nokey"]}]')
    assert cli.parse_additional_vocab(vocab_file) == (
        [{"content": "gnocchi", "sounds_like": ["nokey"]}]
    )

    vocab_file.write_text("[")
    with pytest.raises(SystemExit) as ex:
        cli.parse_additional_vocab(vocab_file)
    exp_msg = f"Additional vocab at: {vocab_file} is not valid json."
    assert ex.value.code == exp_msg

    vocab_file.write_text('{"content": "gnocchi"}')
    with pytest.raises(SystemExit) as ex:
        cli.parse_additional_vocab(vocab_file)
    exp_msg = (
        f"Additional vocab file at: {vocab_file} should be a list of "
        "objects/strings."
    )
    assert ex.value.code == exp_msg

    vocab_file.write_text("[]")
    mock_logger = mocker.patch("speechmatics.cli.LOGGER", autospec=True)
    assert cli.parse_additional_vocab(vocab_file) == []
    mock_logger_warning_str_list = [
        x[0][0] % x[0][1:] for x in mock_logger.warning.call_args_list
    ]
    assert (
        f"Provided additional vocab at: {vocab_file} is an empty list."
        in mock_logger_warning_str_list
    )
    assert len(mock_logger.mock_calls) == 1


@pytest.mark.parametrize(
    "punctuation_permitted_marks, exp_value",
    [
        # the optional punctuation_permitted_marks arg isn't given
        (None, None),
        # an empty string is given to disable all punctuation
        ("", {"permitted_marks": []}),
        # a single space is given to disable all punctuation
        (" ", {"permitted_marks": []}),
        # only commas are allowed
        (",", {"permitted_marks": [","]}),
        ("    ,          ", {"permitted_marks": [","]}),
        # several marks are allowed
        (", . ! ?", {"permitted_marks": [",", ".", "!", "?"]}),
        ("  .  ! ", {"permitted_marks": [".", "!"]}),
    ],
)
def test_get_rt_transcription_config_punctuation_permitted_marks(
    punctuation_permitted_marks, exp_value
):
    args = collections.defaultdict(str)
    args["mode"] = "rt"
    args["punctuation_permitted_marks"] = punctuation_permitted_marks
    config = cli.get_transcription_config(args)
    assert config.punctuation_overrides == exp_value


@pytest.mark.parametrize(
    "enable_partials, exp_value",
    [
        # the optional enable_partials arg isn't given
        # so argparse sets it to False
        (False, None),
        # enable_partials arg was specified
        (True, True),
        # shouldn't happen, but just to be paranoid
        (None, None),
    ],
)
def test_get_transcription_config_enable_partials(enable_partials, exp_value):
    args = collections.defaultdict(str)
    args["mode"] = "rt"
    args["enable_partials"] = enable_partials
    config = cli.get_transcription_config(args)
    assert config.enable_partials == exp_value


def test_additional_vocab_item():
    assert cli_parser.additional_vocab_item("a") == "a"
    assert cli_parser.additional_vocab_item("a:") == {"content": "a"}
    assert cli_parser.additional_vocab_item("a:b,c") == {
        "content": "a",
        "sounds_like": ["b", "c"],
    }
    with pytest.raises(argparse.ArgumentTypeError):
        cli_parser.additional_vocab_item("")
    with pytest.raises(argparse.ArgumentTypeError):
        cli_parser.additional_vocab_item("a:b:c")


def test_get_log_level():
    assert cli.get_log_level(1) == logging.INFO
    assert cli.get_log_level(2) == logging.DEBUG
    for unsupported_log_level in 3, 5:
        with pytest.raises(SystemExit) as ex:
            cli.get_log_level(unsupported_log_level)
        exp_msg = "Only supports 2 log levels eg. -vv, you are asking for -"
        assert ex.value.code == exp_msg + "v" * unsupported_log_level


def test_rt_main_with_basic_options(mock_server):
    args = [
        "-vv",
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        path_to_test_resource("ch.wav"),
    ]
    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent
    assert mock_server.path.startswith("/v2")


def test_rt_main_with_temp_token_option(mock_server):
    args = [
        "-vv",
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        "--generate-temp-token",
        path_to_test_resource("ch.wav"),
    ]
    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent
    assert mock_server.path.startswith("/v2")


def test_rt_main_with_toml_config(mock_server):
    args = [
        "config",
        "set",
        "--auth-token=faketoken",
    ]
    cli.main(vars(cli.parse_args(args)))

    args = [
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        path_to_test_resource("ch.wav"),
    ]
    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()
    print(mock_server.messages_received)
    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent
    assert mock_server.path.startswith("/v2")


def test_rt_main_with_all_options(mock_server, tmp_path):
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text(
        '["jabberwock", {"content": "brillig", "sounds_like": ["brillick"]}]'
    )
    replacement_words_file = tmp_path / "replacement_words.json"
    replacement_words_file.write_text('[{"from": "baz", "to": "quux"}]')

    chunk_size = 1024 * 8
    audio_path = path_to_test_resource("ch.wav")

    args = [
        "-v",
        "--debug",
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--buffer-size=256",
        "--url",
        mock_server.url,
        "--lang=en",
        "--output-locale=en-US",
        "--additional-vocab",
        "tumtum",
        "borogoves:boreohgofes,borrowgoafs",
        "--additional-vocab-file",
        str(vocab_file),
        "--enable-partials",
        "--punctuation-permitted-marks",
        "all",
        "--punctuation-sensitivity",
        "0.1",
        "--diarization",
        "none",
        "--max-delay",
        "5.0",
        "--max-delay-mode",
        "fixed",
        "--chunk-size",
        str(chunk_size),
        "--auth-token=xyz",
        audio_path,
        "--remove-disfluencies",
        "--replacement-words-file",
        str(replacement_words_file),
        "--replacement-words",
        "foo:bar",
        "/regex*/:[redacted]",
    ]

    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent

    # Check that the StartRecognition message contains the correct fields
    msg = mock_server.find_start_recognition_message()

    assert msg["audio_format"]["type"] == "file"
    assert len(msg["audio_format"]) == 1
    assert msg["transcription_config"]["language"] == "en"
    assert msg["transcription_config"]["output_locale"] == "en-US"
    assert msg["transcription_config"]["additional_vocab"] == (
        [
            "jabberwock",
            {"content": "brillig", "sounds_like": ["brillick"]},
            "tumtum",
            {"content": "borogoves", "sounds_like": ["boreohgofes", "borrowgoafs"]},
        ]
    )
    assert mock_server.find_sent_messages_by_type("AddPartialTranscript")
    assert msg["transcription_config"]["punctuation_overrides"]["permitted_marks"] == [
        "all"
    ]  # noqa
    assert (
        msg["transcription_config"]["punctuation_overrides"]["sensitivity"] == 0.1
    )  # noqa
    assert msg["transcription_config"]["diarization"] == "none"
    assert msg["transcription_config"]["max_delay"] == 5.0
    assert msg["transcription_config"]["max_delay_mode"] == "fixed"
    assert msg["transcription_config"].get("operating_point") is None
    assert (
        msg["transcription_config"]["transcript_filtering_config"][
            "remove_disfluencies"
        ]
        is True
    )
    assert msg["transcription_config"]["transcript_filtering_config"][
        "replacements"
    ] == [
        {"from": "baz", "to": "quux"},
        {"from": "foo", "to": "bar"},
        {"from": "/regex*/", "to": "[redacted]"},
    ]

    # Check that the chunk size argument is respected
    add_audio_messages = mock_server.find_add_audio_messages()
    size_of_audio_file = os.stat(audio_path).st_size
    expected_num_messages = size_of_audio_file / chunk_size
    assert -1 <= (len(add_audio_messages) - expected_num_messages) <= 1


def test_rt_main_with_multichannel_option(mock_server):
    chunk_size = 512
    audio_path_1 = path_to_test_resource("ch_converted.wav")
    audio_path_2 = path_to_test_resource("short-text_converted.wav")

    args = [
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        "--diarization=channel",
        "--multichannel=channel_1,channel_2",
        "--lang=en",
        "--chunk-size",
        str(chunk_size),
        "--raw=pcm_s16le",
        "--sample-rate=16000",
        audio_path_1,
        audio_path_2,
    ]

    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent

    # Check that the StartRecognition message contains the correct fields
    msg = mock_server.find_start_recognition_message()

    # Check that audio types are preserved
    assert msg["audio_format"]["type"] == "raw"
    assert msg["audio_format"]["encoding"] == "pcm_s16le"
    assert msg["audio_format"]["sample_rate"] == 16000
    assert msg["transcription_config"]["language"] == "en"
    assert msg["transcription_config"]["diarization"] == "channel"
    assert msg["transcription_config"].get("operating_point") is None
    assert len(msg["transcription_config"]["channel_diarization_labels"]) == 2

    # Check we get all channels in the add channel audio messages
    eoc = mock_server.find_messages_by_type("EndOfChannel")
    assert eoc
    seq_no_map = {m["channel"]: m["last_seq_no"] for m in eoc}
    add_channel_audio_messages = mock_server.find_messages_by_type("AddChannelAudio")
    assert add_channel_audio_messages

    for channel, seq in seq_no_map.items():
        assert seq == sum(
            1 for msg in add_channel_audio_messages if msg.get("channel") == channel
        )

    assert all(
        msg.get("channel") in seq_no_map.keys() for msg in add_channel_audio_messages
    ), "Some messages have invalid channels!"

    # Check file sizes are respected
    size_of_audio_file_1 = os.stat(audio_path_1).st_size
    size_of_audio_file_2 = os.stat(audio_path_2).st_size
    expected_num_messages = ceil(size_of_audio_file_1 / chunk_size) + ceil(
        size_of_audio_file_2 / chunk_size
    )
    assert -1 <= (len(add_channel_audio_messages) - expected_num_messages) <= 1


def test_rt_main_with_config_file(mock_server):
    audio_path = path_to_test_resource("ch.wav")
    config_path = path_to_test_resource("transcription_config.json")

    args = [
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        "--config-file",
        config_path,
        "--auth-token=xyz",
        audio_path,
    ]

    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent

    # Check that the StartRecognition message contains the correct fields
    msg = mock_server.find_start_recognition_message()

    assert msg["audio_format"]["type"] == "file"
    assert len(msg["audio_format"]) == 1
    assert msg["transcription_config"]["language"] == "xy"
    assert msg["transcription_config"]["domain"] == "fake"
    assert msg["transcription_config"]["enable_entities"] is True
    assert msg["transcription_config"].get("operating_point") is None
    assert msg["transcription_config"]["diarization"] == "speaker"
    assert msg["transcription_config"]["speaker_diarization_config"] == {
        "prefer_current_speaker": True,
        "max_speakers": 5,
        "speaker_sensitivity": 0.3,
    }
    assert msg["translation_config"] is not None
    assert msg["translation_config"]["enable_partials"] is False
    assert msg["translation_config"]["target_languages"] == ["es"]


def test_rt_main_with_config_file_cmdline_override(mock_server):
    audio_path = path_to_test_resource("ch.wav")
    config_path = path_to_test_resource("transcription_config.json")

    args = [
        "rt",
        "transcribe",
        "--ssl-mode=insecure",
        "--url",
        mock_server.url,
        "--config-file",
        config_path,
        "--translation-langs=fr",
        "--enable-translation-partials",
        "--auth-token=xyz",
        "--lang=yz",
        "--output-locale=en-US",
        "--domain=different",
        "--operating-point=enhanced",
        "--speaker-diarization-max-speakers=3",
        "--speaker-diarization-sensitivity=0.7",
        audio_path,
    ]

    cli.main(vars(cli.parse_args(args)))
    mock_server.wait_for_clean_disconnects()

    assert mock_server.clients_connected_count == 1
    assert mock_server.clients_disconnected_count == 1
    assert mock_server.messages_received
    assert mock_server.messages_sent

    # Check that the StartRecognition message contains the correct fields
    msg = mock_server.find_start_recognition_message()

    assert msg["audio_format"]["type"] == "file"
    assert len(msg["audio_format"]) == 1
    assert msg["transcription_config"]["language"] == "yz"
    assert msg["transcription_config"]["domain"] == "different"
    assert msg["transcription_config"]["enable_entities"] is True
    assert msg["transcription_config"]["output_locale"] == "en-US"
    assert msg["transcription_config"]["operating_point"] == "enhanced"
    assert msg["transcription_config"]["diarization"] == "speaker"
    assert msg["transcription_config"]["speaker_diarization_config"] == {
        "prefer_current_speaker": True,
        "max_speakers": 3,
        "speaker_sensitivity": 0.7,
    }
    assert msg["translation_config"] is not None
    assert msg["translation_config"]["enable_partials"] is True
    assert msg["translation_config"]["target_languages"] == ["fr"]


@pytest.mark.parametrize(
    "args, values",
    (
        (
            ["config", "set", "--auth-token=faketoken", "--generate-temp-token"],
            {"auth_token": "faketoken", "generate_temp_token": True},
        ),
        (
            ["config", "unset", "--auth-token", "--generate-temp-token"],
            {"auth_token": True, "generate_temp_token": True},
        ),
    ),
)
def test_cli_argparse_config(args, values):
    actual_values = vars(cli.parse_args(args=args))

    for key, val in values.items():
        assert actual_values[key] == val


@pytest.mark.parametrize(
    "args",
    (
        {
            "auth_token": "faketoken",
            "generate_temp_token": True,
        },
        {
            "auth_token": "faketoken",
        },
        {
            "generate_temp_token": True,
        },
        {"generate_temp_token": True, "auth_token": "faketoken", "profile": "test"},
        {"realtime_url": "wss://speechmatics.io"},
        {"batch_url": "https://speechmatics.io"},
    ),
)
def test_config_set_and_remove_toml(args):
    set_args = {"command": "set"}
    set_args = {**set_args, **args}
    try:
        cli.config_main(set_args)
    except Exception:  # pylint: disable=broad-except
        assert False
    home_dir = os.path.expanduser("~")
    cli_config = {}
    with open(f"{home_dir}/.speechmatics/config", "r", encoding="UTF-8") as file:
        cli_config = toml.load(file)
    profile = args.get("profile", "default")
    for key, val in args.items():
        if key != "profile":
            assert cli_config[profile][key] == val

    unset_args = {"command": "unset", "profile": profile}
    for key in ["auth_token", "generate_temp_token", "realtime_url", "batch_url"]:
        if key in args:
            unset_args[key] = True
        else:
            unset_args[key] = False

    try:
        cli.config_main(unset_args)
    except Exception:  # pylint: disable=broad-except
        assert False
    home_dir = os.path.expanduser("~")
    with open(f"{home_dir}/.speechmatics/config", "r", encoding="UTF-8") as file:
        cli_config = toml.load(file)

    for key, val in args.items():
        if key != "profile":
            assert key not in cli_config[profile]


def test_default_urls_connection_config():
    rt_args = {"mode": "rt"}
    settings = cli.get_connection_settings(rt_args, lang="es")
    assert settings.url == f"{RT_SELF_SERVICE_URL}/es"

    batch_args = {"mode": "batch"}
    settings = cli.get_connection_settings(batch_args, lang="es")
    assert settings.url == f"{BATCH_SELF_SERVICE_URL}"
