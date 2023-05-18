# (c) 2020, Cantab Research Ltd.
"""
Functions for converting our JSON transcription results to other formats.
"""
from typing import Any, List


def get_txt_translation(translations: List[dict]):
    """
    Extract translation content and speaker labels to plain text format.

    :param translations: list of dicts containing translation content.
    :return: the plain text as a string.
    """
    sentences = []
    current_speaker = None
    for translation in translations:
        sentence_delimiter = " "
        if translation.get("content", None):
            if (
                translation.get("speaker", None)
                and translation.get("speaker") != current_speaker
            ):
                current_speaker = translation["speaker"]
                sentences.append(f"SPEAKER: {current_speaker}\n")
                sentence_delimiter = "\n"
            sentences.append(translation["content"])
            sentences.append(sentence_delimiter)
    return "".join(sentences).rstrip()


def convert_to_txt(
    tokens: List[dict],
    language: str,
    language_pack_info: dict = None,
    speaker_labels: bool = True,
    speaker_change_token: bool = False,
) -> str:
    """
    Convert a set of transcription result tokens to a plain text format.

    :param tokens: the transcription results.
    :param language_pack_info: information about the language pack.
    :param speaker_labels: whether or not to output speaker labels in the text.
    :return: the plain text as a string.
    """
    # Although we should get word_delimiter from language_pack_info, we still want sensible
    # default behaviour if a customer uses speechmatics-python with an older transcriber which is the
    # reason for a hardcoded default for cmn/ja here.
    word_delimiter = "" if language in ("cmn", "ja") else " "
    if language_pack_info:
        word_delimiter = language_pack_info.get("word_delimiter", word_delimiter)

    groups = group_tokens(tokens)
    current_speaker = None
    texts = []

    for group in groups:
        if not group:
            continue

        # group_tokens always puts speaker_change tokens first in a new group
        if speaker_change_token and group[0]["type"] == "speaker_change":
            if len(group) == 1:
                texts.append("<sc>")
            else:
                texts.append("<sc>\n")

        speaker = get_speaker(group[0])
        if speaker and speaker != current_speaker and speaker_labels:
            current_speaker = speaker
            texts.append(f"SPEAKER: {current_speaker}\n")
        texts.append(join_tokens(group, word_delimiter=word_delimiter))
        texts.append("\n")

    return "".join(texts).rstrip()


def group_tokens(tokens: List[dict]) -> List[List[dict]]:
    """
    Group the tokens in a set of results by speaker (and language if present).
    speaker_change tokens also cause a new group to form.

    :param results: the JSON v2 results
    :return: list of lists
    """
    groups = []
    last = None
    last_is_speaker_change = False
    for token in tokens:
        if token["type"] == "speaker_change":
            groups.append([token])
            last_is_speaker_change = True
            continue
        if last_is_speaker_change or last == (get_speaker(token), get_language(token)):
            groups[-1].append(token)
        else:
            groups.append([token])
        last = (get_speaker(token), get_language(token))
        last_is_speaker_change = False

    return groups


def join_tokens(tokens: List[dict], word_delimiter: str = " ") -> str:
    """
    Join a single group of tokens into plaintext.
    This group is expected to have the same speaker & language.

    :param tokens: the tokens to be joined.
    :param word_delimiter: the character to use for separating tokens (usually " ").
    :return: plain text string
    """
    contents = []
    # Since punctuation can attach to the previous or the next word, this works by grouping
    # words and punctuation marks together into strings which are then just simply joined
    # with the word delimiter.
    current_content = ""
    for token in tokens:
        if token["type"] in {"word", "entity"}:
            contents.append(current_content + get_content(token))
            current_content = ""
        elif token["type"] == "punctuation":
            attachment = token.get("attaches_to", "previous")
            if attachment == "next":
                current_content = get_content(token)
            elif attachment == "previous":
                if contents:
                    contents[-1] += get_content(token)
            elif attachment == "none":
                contents.append(get_content(token))
            elif attachment == "both":
                if contents:
                    current_content = contents.pop() + get_content(token)

    if current_content:
        contents.append(current_content)

    return word_delimiter.join(contents)


def get_property_from_first_alternative(token: dict, prop: str) -> Any:
    """
    Retrieve a property from the first `alternative` in a token, or None if
    there are none or that property does not exist.

    :param token: the token.
    :param prop: the name of the property to lookup.
    :return: the value of the property on the first alternative or None.
    """
    alts = token.get("alternatives", [])
    if not alts:
        return None
    return alts[0].get(prop)


def get_language(token: dict) -> str:
    """
    Get the language of an individual token, if present.

    :param token: the individual token.
    :return: the language or None
    """
    return get_property_from_first_alternative(token, "language")


def get_speaker(token: dict) -> str:
    """
    Get the speaker of an individual token, if present.

    :param token: the individual token.
    :return: the speaker label or None
    """
    return get_property_from_first_alternative(token, "speaker")


def get_content(token: dict) -> str:
    """
    Get the content of an individual token, if present.
    In the case of entity tokens the `written_form` of the token is returned.

    :param token: the individual token.
    :return: the content or None
    """
    if token["type"] == "entity":
        return get_content(token["written_form"][0])
    return get_property_from_first_alternative(token, "content")
