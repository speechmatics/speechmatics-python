#!/usr/bin/env python3
"""Example usage of speechmatics by implementing a CLI."""

import argparse
import json
import logging
import ssl
import sys

from dataclasses import dataclass
from typing import List

from speechmatics.client import WebsocketClient
from speechmatics.models import (
    TranscriptionConfig,
    AudioSettings,
    ClientMessageType,
    ServerMessageType,
    ConnectionSettings,
)

LOGGER = logging.getLogger(__name__)


def print_symbol(symbol):
    """
    Prints a single symbol to standard error.

    Args:
        symbol (str): The symbol to print.
    """
    print(symbol, end="", file=sys.stderr, flush=True)


def parse_additional_vocab(additional_vocab_filepath):
    """
    Parses an additional vocab list from a file.

    Args:
        additional_vocab_filepath (str): Path to the additional vocab file.

    Returns:
        List[Union[dict, str]]: A list of objects or strings which are the
                                additional vocab items.

    Raises:
        SystemExit: If the file is not valid json.
    """
    additional_vocab = []
    with open(additional_vocab_filepath) as additional_vocab_file:
        try:
            additional_vocab = json.load(additional_vocab_file)
        except json.JSONDecodeError:
            raise SystemExit(
                f"Provided additional vocab at: {additional_vocab_filepath} "
                f"is not valid json."
            )

        if not isinstance(additional_vocab, list):
            raise SystemExit(
                (
                    f"Additional vocab file at: {additional_vocab_filepath} "
                    "should be a list of objects/strings."
                )
            )

    if not additional_vocab:
        LOGGER.warning(
            "Provided additional vocab at: %s is an empty list.",
            additional_vocab_filepath,
        )

    return additional_vocab


def additional_vocab_item(to_parse):
    """
    Parses a single item of additional vocab. Used in conjunction with the
    additional vocab command line argument.

    Args:
        to_parse (str): The item to parse.

    Returns:
        Union[dict, str]: Either a dictionary or a string depending on the form
            of the additional vocab item.

    Raises:
        argparse.ArgumentTypeError: If the item to parse is invalid.
    """
    to_parse = str(to_parse)
    parts = to_parse.split(":")
    if len(parts) > 2:
        raise argparse.ArgumentTypeError(
            f"Can't have more than one separator (:) in additional vocab: "
            f"{to_parse}."
        )

    content = parts[0]
    if not content:
        raise argparse.ArgumentTypeError(
            f"Additional vocab must at least have content in: {to_parse}"
        )

    if len(parts) == 1:
        return content

    additional_vocab = {"content": content, "sounds_like": []}

    sounds_likes = parts[1].split(",")
    for sounds_like in sounds_likes:
        if not sounds_like:
            continue
        additional_vocab["sounds_like"].append(sounds_like)

    if not additional_vocab["sounds_like"]:
        del additional_vocab["sounds_like"]

    return additional_vocab


def get_log_level(verbosity):
    """
    Returns the appropriate log level given a verbosity level.

    Args:
        verbosity (int): Verbosity level.

    Returns:
        int: The logging level (e.g. logging.INFO).

    Raises:
        SystemExit: If the given verbosity level is invalid.
    """
    try:
        log_level = {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG}[verbosity]

        return log_level
    except KeyError as error:
        key = int(str(error))
        raise SystemExit(
            f"Only supports 2 log levels eg. -vv, you are asking for "
            f"-{'v' * key}"
        )


@dataclass
class Transcripts:
    text: str
    json: List[dict]


def get_connection_settings(args):
    """
    Helper function which returns a ConnectionSettings object based on the
    command line options given to the program.

    Args:
        args (dict): Keyword arguments, typically from the command line.

    Returns:
        speechmatics.models.ConnectionSettings: Settings for the WebSocket
            connection.
    """
    settings = ConnectionSettings(
        url=args["url"], message_buffer_size=args["buffer_size"]
    )
    if args["ssl_mode"] == "insecure":
        settings.ssl_context.check_hostname = False
        settings.ssl_context.verify_mode = ssl.CERT_NONE
    elif args["ssl_mode"] == "none":
        settings.ssl_context = None

    return settings


def get_transcription_config(args):
    """
    Helper function which returns a TranscriptionConfig object based on the
    command line options given to the program.

    Args:
        args (dict): Keyword arguments probably from the command line.

    Returns:
        speechmatics.models.TranscriptionConfig: Settings for the ASR engine.
    """
    config = TranscriptionConfig(
        args["lang"],
        enable_partials=True if args["enable_partials"] else None,
        output_locale=args["output_locale"],
        max_delay=args["max_delay"],
        diarization=args["diarization"],
        speaker_change_sensitivity=args["speaker_change_sensitivity"],
        n_best_limit=args["n_best_limit"],
    )

    if args["additional_vocab_file"]:
        additional_vocab = parse_additional_vocab(args["additional_vocab_file"])
        config.additional_vocab = additional_vocab
        LOGGER.info(
            "Using additional vocab from file %s", args["additional_vocab_file"]
        )

    if args["additional_vocab"]:
        if not config.additional_vocab:
            config.additional_vocab = args["additional_vocab"]
        else:
            config.additional_vocab.extend(args["additional_vocab"])
        LOGGER.info(
            "Using additional vocab from args %s", args["additional_vocab"])

    if args["punctuation_permitted_marks"] is not None \
            or args["punctuation_sensitivity"]:
        config.punctuation_overrides = {}

        if args["punctuation_permitted_marks"] is not None:
            config.punctuation_overrides["permitted_marks"] = args[
                "punctuation_permitted_marks"
            ].split()

        if args["punctuation_sensitivity"]:
            config.punctuation_overrides["sensitivity"] = args[
                "punctuation_sensitivity"
            ]

    return config


def get_audio_settings(args):
    """
    Helper function which returns an AudioSettings object based on the command
    line options given to the program.

    Args:
        args (dict): Keyword arguments, typically from the command line.

    Returns:
        speechmatics.models.TranscriptionConfig: Settings for the audio stream
            in the connection.
    """
    settings = AudioSettings(
        sample_rate=args["sample_rate"],
        chunk_size=args["chunk_size"],
        encoding=args["raw"],
    )
    return settings


# pylint: disable=too-many-arguments
def add_printing_handlers(
        api, transcripts, enable_partials=False, debug_handlers_too=False,
        speaker_change_token=False, language="en"):
    """
    Adds a set of handlers to the websocket client which print out transcripts
    as they are received. This includes partials if they are enabled.

    Args:
        api (speechmatics.client.WebsocketClient): Client instance.
        transcripts (Transcripts): Allows the transcripts to be concatenated to
            produce a final result.
        enable_partials (bool, optional): Whether or not partials are enabled.
        debug_handlers_too (bool, optional): Whether or not to enable 'debug'
            handlers that print out an ASCII symbol representing messages being
            received and sent.
        speaker_change_token (bool, optional): Whether to explicitly include a
            speaker change token '<sc>' in the output to indicate speaker
            changes.
        language (string, optional): The language code of the model being used.
            This is needed to configure language-specific text formatting.
    """
    if debug_handlers_too:
        api.add_event_handler(
            ServerMessageType.AudioAdded, lambda *args: print_symbol("-")
        )
        api.add_event_handler(
            ServerMessageType.AddPartialTranscript,
            lambda *args: print_symbol(".")
        )
        api.add_event_handler(
            ServerMessageType.AddTranscript,
            lambda *args: print_symbol("|")
        )
        api.add_middleware(
            ClientMessageType.AddAudio,
            lambda *args: print_symbol("+")
        )

    def partial_transcript_handler(message):
        # "\n" does not appear in partial transcripts
        print(f'{message["metadata"]["transcript"]}', end="\r", file=sys.stderr)

    def transcript_handler(message):
        transcripts.json.append(message)
        transcript = message["metadata"]["transcript"]
        if transcript:
            transcript_to_print = transcript
            if speaker_change_token:
                transcript_with_sc_token = transcript.replace("\n", "\n<sc>\n")
                transcript_to_print = transcript_with_sc_token
            transcripts.text += transcript_to_print
            print(transcript_to_print)

        n_best_results = message.get("n_best_results", [])
        if n_best_results:
            n_best_list = n_best_results[0]["n_best_list"]
            for alternative in n_best_list:
                words_joined = join_words(
                    (word["content"] for word in alternative["words"]),
                    language=language,
                )
                print("* [{:.4f}] {}".format(
                    alternative["confidence"], words_joined))
            print()

    def end_of_transcript_handler(_):
        if enable_partials:
            print("\n", file=sys.stderr)

    api.add_event_handler(
        ServerMessageType.AddPartialTranscript, partial_transcript_handler
    )
    api.add_event_handler(
        ServerMessageType.AddTranscript, transcript_handler)
    api.add_event_handler(
        ServerMessageType.EndOfTranscript, end_of_transcript_handler)


def join_words(words, language="en"):
    """
    Joins a list of words with a language specific separator. Because not all
    languages use the standard English white-space between words.

    Args:
        words (List[str]): List of words
        language (str): Language code

    Returns:
        str: Words joined with a language-specific separator.
    """
    if language in {"ja", "cmn"}:
        separator = ""
    else:
        separator = " "
    return separator.join(words)


def main(args=None):
    """
    Main entrypoint.

    Args:
        args (List[str]): command-line arguments; defaults to None in which
            case arguments will retrieved from `sys.argv` (this is useful
            mainly for unit tests).
    """
    if not args:
        args = vars(parse_args())

    logging.basicConfig(level=get_log_level(args["verbose"]))
    LOGGER.info("Args: %s", args)

    api = WebsocketClient(get_connection_settings(args))

    if args["url"].lower().startswith("ws://") and args["ssl_mode"] != "none":
        raise SystemExit(
            f"ssl_mode '{args['ssl_mode']}' is incompatible with protocol 'ws'."
            "Use 'wss' instead."
        )
    if args["url"].lower().startswith("wss://") and args["ssl_mode"] == "none":
        raise SystemExit(
            f"ssl_mode 'none' is incompatible with protocol 'wss'. "
            f"Use 'ws' instead."
        )

    transcripts = Transcripts(text="", json=[])
    add_printing_handlers(
        api,
        transcripts,
        enable_partials=args["enable_partials"],
        debug_handlers_too=args["debug"],
        speaker_change_token=args["speaker_change_token"],
        language=args["lang"],
    )

    def run(stream):
        try:
            api.run_synchronously(
                stream, get_transcription_config(args), get_audio_settings(args)
            )
        except KeyboardInterrupt:
            # Gracefully handle Ctrl-C, else we get a huge stack-trace.
            LOGGER.warning("Keyboard interrupt received.")

    if args["files"][0] == "-":
        run(sys.stdin.buffer)
    else:
        for filename in args["files"]:
            with open(filename, "rb") as audio_file:
                run(audio_file)


def parse_args(args=None):
    """
    Parses command-line arguments.

    Arguments:
        args: (List[str], optional): List of arguments to parse.

    Returns:
        Namespace: The set of arguments provided along with their values.
    """
    parser = argparse.ArgumentParser(description="Transcribe a file")
    parser.add_argument(
        "-v",
        dest="verbose",
        action="count",
        default=0,
        help=(
            "Set the log level for verbose logs. "
            "The number of flags indicate the level, eg. "
            "-v is INFO and -vv is DEBUG."
        ),
    )
    parser.add_argument(
        "--ssl-mode",
        default="regular",
        choices=["regular", "insecure", "none"],
        help=(
            "Use a preset configuration for the SSL context. With `regular` "
            "mode a valid certificate is expected. With `insecure` mode a self "
            "signed certificate is allowed. With `none` then SSL is not used."
        ),
    )
    parser.add_argument(
        "--buffer-size",
        default=512,
        type=int,
        help=(
            "Maximum number of messages to send before waiting for "
            "acknowledgements from the server."
        ),
    )
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help=(
            "Prints useful symbols to represent the messages on the wire. "
            "Symbols are printed to STDERR, use only when STDOUT is "
            "redirected to a file."
        ),
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Websockets URL (e.g. wss://192.168.8.12:9000/)",
    )
    parser.add_argument(
        "--lang", type=str, default="en",
        help="Language (ISO code, e.g. en, fr, de)"
    )
    parser.add_argument(
        "--output-locale",
        metavar="LOCALE",
        type=str,
        default=None,
        help="Locale of the output of transcripts. eg. en-US",
    )
    parser.add_argument(
        "--additional-vocab",
        nargs="*",
        type=additional_vocab_item,
        help=(
            "Space separated list of additional vocab. Expected format: "
            "<content (required)>:<sounds like (optional)>,<anymore sounds "
            "like> Simple vocab list example: 'Speechmatics gnocchi'. "
            "Vocab list with sounds like example: 'gnocchi:nokey,nochi'."
        ),
    )
    parser.add_argument(
        "--additional-vocab-file",
        metavar="VOCAB_FILEPATH",
        type=str,
        help="File with additional vocab in JSON format",
    )
    parser.add_argument("--enable-partials", default=False, action="store_true")
    parser.add_argument(
        "--punctuation-permitted-marks",
        type=str,
        default=None,
        help=(
            "Space separated list of permitted punctuation marks for advanced "
            "punctuation."
        ),
    )
    parser.add_argument(
        "--punctuation-sensitivity",
        type=float,
        help="Sensitivity level for advanced punctuation.",
    )
    parser.add_argument(
        "--diarization",
        choices=["none", "speaker_change"],
        help="Which type of diarization to use.",
    )
    parser.add_argument(
        "--speaker-change-sensitivity",
        type=float,
        help="Sensitivity level for speaker change.",
    )
    parser.add_argument(
        "--speaker-change-token",
        default=False,
        action="store_true",
        help="Shows a <sc> token where a speaker change was detected.",
    )
    parser.add_argument("--max-delay", type=float)
    parser.add_argument(
        "--raw",
        metavar="ENCODING",
        type=str,
        help=(
            "Indicate that the input audio is raw, provide the encoding of "
            "this raw audio, eg. pcm_f32le"
        ),
    )
    parser.add_argument("--sample-rate", type=int, default=44_100)
    parser.add_argument("--chunk-size", type=int, default=1024*4)
    parser.add_argument(
        "--n-best-limit",
        type=int,
        default=None,
        help="Upper bound on the number of N-best alternatives to return for "
        "each final. If not specified, N-best output is disabled. Be aware that"
        " this option is not supported for all Speechmatics products.",
    )
    parser.add_argument(
        "files", metavar="FILEPATHS", type=str, nargs="+",
        help="File(s) to process"
    )

    return parser.parse_args(args=args)
