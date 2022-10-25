import argparse
import collections
import copy
import logging
import os

import pytest

from speechmatics import cli
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
            {"language": "en", "output_locale": "en-GB"},
        ),
        (
            ["batch", "transcribe", "--output-locale", "en-GB"],
            {"language": "en", "output_locale": "en-GB"},
        ),
        (
            ["rt", "transcribe", "--additional-vocab", "Speechmatics", "gnocchi"],
            {"additional_vocab": ["Speechmatics", "gnocchi"]},
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
        (["rt", "transcribe", "--enable-entities"], {"enable_entities": True}),
        (["batch", "transcribe", "--enable-entities"], {"enable_entities": True}),
        (
            ["batch", "transcribe", "--speaker-diarization-sensitivity=0.7"],
            {"speaker_diarization_sensitivity": 0.7},
        ),
        (
            ["rt", "transcribe", "--speaker-change-token"],
            {"speaker_change_token": True},
        ),
        (
            [
                "rt",
                "transcribe",
                "--diarization=speaker",
                "--speaker-diarization-max-speakers=3",
            ],
            {"diarization": "speaker", "speaker_diarization_max_speakers": 3},
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
        (
            [
                "batch",
                "transcribe",
                "--diarization=channel_and_speaker_change",
                "--channel-diarization-labels=label1 label2",
            ],
            {
                "diarization": "channel_and_speaker_change",
                "channel_diarization_labels": ["label1 label2"],
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
        (
            ["batch", "transcribe", "--diarization=channel_and_speaker_change"],
            {"diarization": "channel_and_speaker_change"},
        ),
        (["batch", "submit"], {"command": "submit"}),
    ],
)
def test_cli_arg_parse_with_file(args, values):
    connection_args = ["--url=example", "--auth-token=xyz"]
    test_args = args + connection_args + ["fake_file.wav"]
    actual_values = vars(cli.parse_args(args=test_args))

    for (key, val) in values.items():
        assert actual_values[key] == val


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

    for (key, val) in values.items():
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

    for (key, val) in values.items():
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
    assert cli.additional_vocab_item("a") == "a"
    assert cli.additional_vocab_item("a:") == {"content": "a"}
    assert cli.additional_vocab_item("a:b,c") == {
        "content": "a",
        "sounds_like": ["b", "c"],
    }
    with pytest.raises(argparse.ArgumentTypeError):
        cli.additional_vocab_item("")
    with pytest.raises(argparse.ArgumentTypeError):
        cli.additional_vocab_item("a:b:c")


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
    assert mock_server.path == "/v2"


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
    assert mock_server.path == "/v2"


def test_rt_main_with_all_options(mock_server, tmp_path):
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text(
        '["jabberwock", {"content": "brillig", "sounds_like": ["brillick"]}]'
    )

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
        "--speaker-change-sensitivity",
        "0.8",
        "--speaker-change-token",
        "--max-delay",
        "5.0",
        "--max-delay-mode",
        "fixed",
        "--chunk-size",
        str(chunk_size),
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
    assert msg["transcription_config"]["speaker_change_sensitivity"] == 0.8

    # Check that the chunk size argument is respected
    add_audio_messages = mock_server.find_add_audio_messages()
    size_of_audio_file = os.stat(audio_path).st_size
    expected_num_messages = size_of_audio_file / chunk_size
    assert -1 <= (len(add_audio_messages) - expected_num_messages) <= 1


def test_add_printing_handlers_transcript_handler(mocker, capsys):
    api = mocker.MagicMock()
    api.get_language_pack_info = mocker.MagicMock(return_value={"word_delimiter": " "})
    transcripts = cli.Transcripts(text="", json=[])

    cli.add_printing_handlers(api, transcripts)
    assert not transcripts.text
    assert not transcripts.json
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert api.add_event_handler.called
    call_args_dict = {i[0][0]: i[0][1] for i in api.add_event_handler.call_args_list}

    finals_msg_type = "AddTranscript"
    assert finals_msg_type in call_args_dict
    transcript_handler_cb_func = call_args_dict[finals_msg_type]

    transcript = ""
    msg_empty_transcript = {
        "message": "AddTranscript",
        "results": [],
        "metadata": {
            "start_time": 58.920005798339844,
            "end_time": 60.0000057220459,
            "transcript": transcript,
        },
        "format": "2.4",
    }
    transcript_handler_cb_func(msg_empty_transcript)
    assert transcripts.text == transcript
    assert transcripts.json == [msg_empty_transcript]
    out, err = capsys.readouterr()
    assert not out, "Don't print a newline when the transcript is empty"
    assert not err

    transcript = "Howdy"
    msg_single_word_transcript = copy.deepcopy(msg_empty_transcript)
    msg_single_word_transcript["metadata"]["transcript"] = transcript
    msg_single_word_transcript["results"].append(
        {
            "type": "word",
            "start_time": 0.08999999612569809,
            "end_time": 0.29999998211860657,
            "alternatives": [
                {"confidence": 1.0, "content": transcript.strip(), "language": "en"}
            ],
        }
    )
    transcript_handler_cb_func(msg_single_word_transcript)
    assert transcripts.text == transcript
    assert transcripts.json == [msg_empty_transcript, msg_single_word_transcript]
    out, err = capsys.readouterr()
    assert out == transcript + "\n"
    assert not err

    transcript_handler_cb_func(msg_empty_transcript)
    transcript_handler_cb_func(msg_single_word_transcript)
    transcript_handler_cb_func(msg_empty_transcript)
    assert transcripts.text == transcript * 2
    assert transcripts.json == [
        msg_empty_transcript,
        msg_single_word_transcript,
        msg_empty_transcript,
        msg_single_word_transcript,
        msg_empty_transcript,
    ]
    out, err = capsys.readouterr()
    assert out == transcript + "\n"
    assert not err


TRANSCRIPT_TXT_WITH_SC = "Hey\nHello"
TRANSCRIPT_WITH_SC = {
    "message": "AddTranscript",
    "results": [
        {
            "type": "word",
            "start_time": 0.08999999612569809,
            "end_time": 0.29999998211860657,
            "alternatives": [{"confidence": 1.0, "content": "Hey", "language": "en"}],
        },
        {
            "type": "speaker_change",
            "start_time": 0.08999999612569809,
            "end_time": 0.29999998211860657,
            "score": 1,
        },
        {
            "type": "word",
            "start_time": 0.08999999612569809,
            "end_time": 0.29999998211860657,
            "alternatives": [{"confidence": 1.0, "content": "Hello", "language": "en"}],
        },
    ],
    "metadata": {
        "start_time": 58.920005798339844,
        "end_time": 60.0000057220459,
        "transcript": TRANSCRIPT_TXT_WITH_SC,
    },
    "format": "2.4",
}


def check_printing_handlers(
    mocker, capsys, transcript, expected_transcript_txt, speaker_change_token
):
    api = mocker.MagicMock()
    api.get_language_pack_info = mocker.MagicMock(return_value={"word_delimiter": " "})
    transcripts = cli.Transcripts(text="", json=[])

    cli.add_printing_handlers(
        api, transcripts, speaker_change_token=speaker_change_token
    )
    assert not transcripts.text
    assert not transcripts.json
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert api.add_event_handler.called
    call_args_dict = {i[0][0]: i[0][1] for i in api.add_event_handler.call_args_list}

    finals_msg_type = "AddTranscript"
    assert finals_msg_type in call_args_dict
    transcript_handler_cb_func = call_args_dict[finals_msg_type]

    transcript_handler_cb_func(transcript)
    assert transcripts.text == expected_transcript_txt
    assert transcripts.json == [transcript]
    out, err = capsys.readouterr()
    assert out == expected_transcript_txt + "\n"
    assert not err


def test_add_printing_handlers_with_speaker_change_token(mocker, capsys):
    expected_transcript = "Hey\n<sc>\nHello"
    check_printing_handlers(
        mocker,
        capsys,
        TRANSCRIPT_WITH_SC,
        expected_transcript,
        speaker_change_token=True,
    )


def test_add_printing_handlers_with_speaker_change_no_token(mocker, capsys):
    expected_transcript = "Hey\nHello"
    check_printing_handlers(
        mocker,
        capsys,
        TRANSCRIPT_WITH_SC,
        expected_transcript,
        speaker_change_token=False,
    )
