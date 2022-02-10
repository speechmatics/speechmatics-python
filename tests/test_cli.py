import argparse
import collections
import copy
import logging
import os

import pytest

import speechmatics.cli as cli
from tests.utils import path_to_test_resource


@pytest.mark.parametrize(
    "args, values",
    [
        (
            ["transcribe"],
            {
                "ssl_mode": "regular",
                "enable_partials": False,
                "punctuation_permitted_marks": None,
            },
        ),
        (["-v", "transcribe"], {"verbose": 1}),
        (["-vv", "transcribe"], {"verbose": 2}),
        (["transcribe", "--ssl-mode=insecure"], {"ssl_mode": "insecure"}),
        (["transcribe", "--ssl-mode=none"], {"ssl_mode": "none"}),
        (["transcribe", "--additional-vocab"], {"additional_vocab": []}),
        (
            ["transcribe", "--additional-vocab", "Speechmatics", "gnocchi"],
            {"additional_vocab": ["Speechmatics", "gnocchi"]},
        ),
        (
            [
                "transcribe",
                "--additional-vocab",
                "gnocchi:nokey,nochi",
                "Speechmatics:speechmadticks",
            ],
            {
                "additional_vocab": [
                    {"content": "gnocchi", "sounds_like": ["nokey", "nochi"]},
                    {
                        "content": "Speechmatics",
                        "sounds_like": ["speechmadticks"]
                    },
                ]
            },
        ),
        (
            ["transcribe", "--punctuation-permitted-marks", ", ? ."],
            {"punctuation_permitted_marks": ", ? ."},
        ),
        (
            ["transcribe", "--punctuation-permitted-marks", ""],
            {"punctuation_permitted_marks": ""}
        ),
        (["transcribe", "--enable-partials"], {"enable_partials": True}),
        (["transcribe", "--enable-entities"], {"enable_entities": True}),
        (
            ["transcribe", "--speaker-change-token"],
            {"speaker_change_token": True}
        ),
        (["transcribe", "--n-best-limit=5"], {"n_best_limit": 5}),
        (["transcribe", "--auth-token=xyz"], {"auth_token": "xyz"}),
        (
            ["transcribe", "--operating-point=standard"],
            {"operating_point": "standard"},
        ),
        (
            ["transcribe", "--operating-point=enhanced"],
            {"operating_point": "enhanced"},
        ),
    ],
)
def test_cli_arg_parse(args, values):
    required_args = ["--url=example", "file"]
    test_args = args + required_args
    actual_values = vars(cli.parse_args(args=test_args))

    for (key, val) in values.items():
        assert actual_values[key] == val


def test_parse_additional_vocab(tmp_path, mocker):
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text('["Speechmatics", "gnocchi"]')
    assert cli.parse_additional_vocab(vocab_file) == (
        ["Speechmatics", "gnocchi"]
    )

    vocab_file.write_text('[{"content": "gnocchi", "sounds_like": ["nokey"]}]')
    assert cli.parse_additional_vocab(vocab_file) == (
        [{"content": "gnocchi", "sounds_like": ["nokey"]}]
    )

    vocab_file.write_text("[")
    with pytest.raises(SystemExit) as ex:
        cli.parse_additional_vocab(vocab_file)
    exp_msg = ('Provided additional vocab at: {} is not valid json.'
               .format(vocab_file))
    assert ex.value.code == exp_msg

    vocab_file.write_text('{"content": "gnocchi"}')
    with pytest.raises(SystemExit) as ex:
        cli.parse_additional_vocab(vocab_file)
    exp_msg = ('Additional vocab file at: {} should be a list of '
               'objects/strings.'.format(vocab_file))
    assert ex.value.code == exp_msg

    vocab_file.write_text('[]')
    mock_logger = mocker.patch('speechmatics.cli.LOGGER', autospec=True)
    assert cli.parse_additional_vocab(vocab_file) == []
    mock_logger_warning_str_list = [x[0][0] % x[0][1:] for x in
                                    mock_logger.warning.call_args_list]
    assert (
        'Provided additional vocab at: {} is an empty list.'.format(vocab_file)
    ) in mock_logger_warning_str_list
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
def test_get_transcription_config_punctuation_permitted_marks(
        punctuation_permitted_marks, exp_value
):
    args = collections.defaultdict(str)
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
        exp_msg = 'Only supports 2 log levels eg. -vv, you are asking for -'
        assert ex.value.code == exp_msg + 'v' * unsupported_log_level


def test_main_with_basic_options(mock_server):
    args = [
        "-vv",
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
    assert mock_server.connection_request.path == "/v2"


def test_main_with_all_options(mock_server, tmp_path):
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text(
        '["jabberwock", {"content": "brillig", "sounds_like": ["brillick"]}]'
    )

    chunk_size = 1024 * 8
    audio_path = path_to_test_resource("ch.wav")

    args = [
        "-v",
        "transcribe",
        "--ssl-mode=insecure",
        "--buffer-size=256",
        "--debug",
        "--url",
        "wss://127.0.0.1:8765/v2",
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
    print(msg)
    assert msg["audio_format"]["type"] == "file"
    assert len(msg["audio_format"]) == 1
    assert msg["transcription_config"]["language"] == "en"
    assert msg["transcription_config"]["output_locale"] == "en-US"
    assert msg["transcription_config"]["additional_vocab"] == (
        [
            "jabberwock",
            {"content": "brillig", "sounds_like": ["brillick"]},
            "tumtum", {
                "content": "borogoves", "sounds_like": [
                    "boreohgofes", "borrowgoafs"
                ]
            },
        ]
    )
    assert mock_server.find_sent_messages_by_type("AddPartialTranscript")
    assert msg["transcription_config"]["punctuation_overrides"]["permitted_marks"] == [  # noqa
        "all"
    ]
    assert msg["transcription_config"]["punctuation_overrides"]["sensitivity"] == 0.1  # noqa
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
    transcripts = cli.Transcripts(text="", json=[])

    cli.add_printing_handlers(api, transcripts)
    assert not transcripts.text
    assert not transcripts.json
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert api.add_event_handler.called
    call_args_dict = {
        i[0][0]: i[0][1] for i in api.add_event_handler.call_args_list
    }

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

    transcript = "Howdy "
    msg_single_word_transcript = copy.deepcopy(msg_empty_transcript)
    msg_single_word_transcript["metadata"]["transcript"] = transcript
    msg_single_word_transcript["results"].append(
        {
            "type": "word",
            "start_time": 0.08999999612569809,
            "end_time": 0.29999998211860657,
            "alternatives": [
                {
                    "confidence": 1.0, "content": transcript.strip(),
                    "language": "en"
                }
            ],
        }
    )
    transcript_handler_cb_func(msg_single_word_transcript)
    assert transcripts.text == transcript
    assert transcripts.json == \
        [msg_empty_transcript, msg_single_word_transcript]
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
            "alternatives": [
                {"confidence": 1.0, "content": "Hey", "language": "en"}
            ],
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
            "alternatives": [
                {"confidence": 1.0, "content": "Hello", "language": "en"}
            ],
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
        mocker, capsys, transcript, expected_transcript_txt,
        speaker_change_token
):
    api = mocker.MagicMock()
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
    call_args_dict = {
        i[0][0]: i[0][1] for i in api.add_event_handler.call_args_list
    }

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
