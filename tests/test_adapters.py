import json
import os

import pytest

from speechmatics import adapters
from tests.utils import path_to_test_resource


@pytest.mark.parametrize(
    "json_name, txt_name, language_pack_info, speaker_labels",
    [
        ("empty.json", "empty.txt", {"word_delimiter": " "}, False),
        ("simple_case.json", "simple_case.txt", {"word_delimiter": " "}, False),
        (
            "simple_case.json",
            "simple_case_with_speakers.txt",
            {"word_delimiter": " "},
            True,
        ),
        (
            "simple_case.json",
            "simple_case_no_word_delim.txt",
            {"word_delimiter": ""},
            False,
        ),
        (
            "two_speakers.json",
            "two_speakers.txt",
            {"word_delimiter": " "},
            False,
        ),
        (
            "two_speakers.json",
            "two_speakers_with_speaker_labels.txt",
            {"word_delimiter": " "},
            True,
        ),
        ("entity.json", "entity.txt", {"word_delimiter": " "}, False),
        ("punctuation.json", "punctuation.txt", {"word_delimiter": " "}, False),
    ],
)
def test_convert_to_txt(
    json_name: str,
    txt_name: str,
    language_pack_info: dict,
    speaker_labels: bool,
):
    json_file_path = path_to_test_resource(os.path.join("convert_to_txt", json_name))
    txt_file_path = path_to_test_resource(os.path.join("convert_to_txt", txt_name))

    with open(json_file_path, "r", encoding="utf-8") as json_fh:
        data = json.load(json_fh)

    with open(txt_file_path, "r", encoding="utf-8") as txt_fh:
        txt = txt_fh.read()

    assert (
        adapters.convert_to_txt(
            data["results"],
            "en",
            language_pack_info,
            speaker_labels,
        )
        == txt
    )
