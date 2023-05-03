import copy
import sys

import pytest

from speechmatics import cli
from speechmatics.models import ServerMessageType, TranslationConfig


@pytest.mark.parametrize("check_tty", [False, True])
def test_add_printing_handlers_transcript_handler(mocker, capsys, check_tty):
    # patch in isatty, in order to check behaviour with and without tty
    sys.stderr.isatty = lambda: check_tty
    sys.stdout.isatty = lambda: check_tty

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

    finals_msg_type = ServerMessageType.AddTranscript.value
    assert finals_msg_type in call_args_dict
    transcript_handler_cb_func = call_args_dict[finals_msg_type]

    transcript = ""
    msg_empty_transcript = {
        "message": finals_msg_type,
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

    escape_seq = "\33[2K" if sys.stdout.isatty() else ""
    assert out == escape_seq + transcript + "\n"
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

    escape_seq = "\33[2K" if sys.stdout.isatty() else ""
    out, err = capsys.readouterr()
    assert out == escape_seq + transcript + "\n"
    assert not err


@pytest.mark.parametrize("check_tty", [False, True])
def test_add_printing_handlers_translation_handler(mocker, capsys, check_tty):
    # patch in isatty, in order to check behaviour with and without tty
    sys.stderr.isatty = lambda: check_tty
    sys.stdout.isatty = lambda: check_tty

    api = mocker.MagicMock()
    transcripts = cli.Transcripts(text="", json=[])
    translation_config = TranslationConfig(target_languages=["fr"])
    cli.add_printing_handlers(
        api=api, transcripts=transcripts, translation_config=translation_config
    )
    assert not transcripts.text
    assert not transcripts.json
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert api.add_event_handler.called
    call_args_dict = {i[0][0]: i[0][1] for i in api.add_event_handler.call_args_list}

    finals_msg_type = ServerMessageType.AddTranslation.value
    assert finals_msg_type in call_args_dict
    transcript_handler_cb_func = call_args_dict[finals_msg_type]

    transcript = ""
    msg_empty_transcript = {
        "message": finals_msg_type,
        "language": "fr",
        "results": [
            {"start_time": 0.8099999, "end_time": 2.3099999, "content": transcript}
        ],
    }
    transcript_handler_cb_func(msg_empty_transcript)
    assert transcripts.text == transcript
    assert transcripts.json == [msg_empty_transcript]

    out, err = capsys.readouterr()
    assert not out, "Don't print a newline when the transcript is empty"
    assert not err

    transcript = "Bonjour"
    msg_single_word_transcript = copy.deepcopy(msg_empty_transcript)
    msg_single_word_transcript["results"][0]["content"] = transcript
    transcript_handler_cb_func(msg_single_word_transcript)
    assert transcripts.text == transcript
    assert transcripts.json == [msg_empty_transcript, msg_single_word_transcript]
    out, err = capsys.readouterr()

    escape_seq = "\33[2K" if sys.stdout.isatty() else ""
    assert out == escape_seq + transcript + "\n"
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

    escape_seq = "\33[2K" if sys.stdout.isatty() else ""
    out, err = capsys.readouterr()
    assert out == escape_seq + transcript + "\n"
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
    mocker,
    capsys,
    transcript,
    expected_transcript_txt,
    speaker_change_token,
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

    escape_seq = "\33[2K" if sys.stdout.isatty() else ""
    out, err = capsys.readouterr()
    assert out == escape_seq + expected_transcript_txt + "\n"
    assert not err


@pytest.mark.parametrize("check_tty", [False, True])
def test_add_printing_handlers_with_speaker_change_token(mocker, capsys, check_tty):
    # patch in isatty, in order to check behaviour with and without tty
    sys.stderr.isatty = lambda: check_tty
    sys.stdout.isatty = lambda: check_tty

    expected_transcript = "Hey\n<sc>\nHello"
    check_printing_handlers(
        mocker,
        capsys,
        TRANSCRIPT_WITH_SC,
        expected_transcript,
        speaker_change_token=True,
    )


@pytest.mark.parametrize("check_tty", [False, True])
def test_add_printing_handlers_with_speaker_change_no_token(mocker, capsys, check_tty):
    # patch in isatty, in order to check beheviour with and without tty
    sys.stderr.isatty = lambda: check_tty
    sys.stdout.isatty = lambda: check_tty

    expected_transcript = "Hey\nHello"
    check_printing_handlers(
        mocker,
        capsys,
        TRANSCRIPT_WITH_SC,
        expected_transcript,
        speaker_change_token=False,
    )
