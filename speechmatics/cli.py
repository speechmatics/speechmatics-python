#!/usr/bin/env python3
# (c) 2020, Cantab Research Ltd.
"""
Command-line interface
"""

import argparse
import json
import logging
import os
import ssl
import sys

from dataclasses import dataclass
from typing import List, Dict, Union, Tuple, Any
from urllib.parse import urlparse

import speechmatics.adapters
from speechmatics.client import WebsocketClient
from speechmatics.batch_client import BatchClient
from speechmatics.models import (
    TranscriptionConfig,
    AudioSettings,
    ClientMessageType,
    ServerMessageType,
    ConnectionSettings,
    BatchTranscriptionConfig,
    BatchSpeakerDiarizationConfig,
    RTSpeakerDiarizationConfig,
)

LOGGER = logging.getLogger(__name__)


def print_symbol(symbol):
    """
    Prints a single symbol to standard error.

    :param symbol: The symbol to print.
    :type symbol: str
    """
    print(symbol, end="", file=sys.stderr, flush=True)


def parse_additional_vocab(additional_vocab_filepath):
    """
    Parses an additional vocab list from a file.

    :param additional_vocab_filepath: Path to the additional vocab file.
    :type additional_vocab_filepath: str

    :return: A list of objects or strings which are the additional
        vocab items.
    :rtype: List[Union[dict, str]]

    :raises SystemExit: If the file is not valid JSON.
    """
    additional_vocab = []
    with open(additional_vocab_filepath, encoding="utf-8") as additional_vocab_file:
        try:
            additional_vocab = json.load(additional_vocab_file)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"Additional vocab at: {additional_vocab_filepath} "
                f"is not valid json."
            ) from exc

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

    :param to_parse: The item to parse.
    :type to_parse: str

    :return: Either a dictionary or a string depending on the form of the
        additional vocab item.
    :rtype: Union[dict, str]

    :raises argparse.ArgumentTypeError: If the item to parse is invalid.
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
            f"Additional vocab must have content in: {to_parse}"
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

    :param verbosity: Verbosity level.
    :type verbosity: int

    :return: The logging level (eg. logging.INFO).
    :rtype: int

    :raises SystemExit: If the given verbosity level is invalid.
    """
    try:
        log_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[verbosity]

        return log_level
    except KeyError as error:
        key = int(str(error))
        raise SystemExit(
            f"Only supports 2 log levels eg. -vv, you are asking for " f"-{'v' * key}"
        ) from error


@dataclass
class Transcripts:
    text: str
    json: List[dict]


def get_connection_settings(args):
    """
    Helper function which returns a ConnectionSettings object based on the
    command line options given to the program.

    :param args: Keyword arguments, typically from the command line.
    :type args: dict

    :return: Settings for the WebSocket connection.
    :rtype: speechmatics.models.ConnectionSettings
    """
    settings = ConnectionSettings(
        url=args.get("url"),
        auth_token=args.get("auth_token"),
        generate_temp_token=True if args.get("generate_temp_token", False) else None,
    )

    if args.get("buffer_size") is not None:
        settings.message_buffer_size = args["buffer_size"]

    if args.get("ssl_mode") == "insecure":
        settings.ssl_context.check_hostname = False
        settings.ssl_context.verify_mode = ssl.CERT_NONE
    elif args.get("ssl_mode") == "none":
        settings.ssl_context = None

    return settings


def get_transcription_config(args):
    """
    Helper function which returns a TranscriptionConfig object based on the
    command line options given to the program.

    :param args: Keyword arguments probably from the command line.
    :type args: dict

    :return: Settings for the ASR engine.
    :rtype: speechmatics.models.TranscriptionConfig |
    speechmatics.models.BatchTranscriptionConfig
    """
    config = dict(
        language=args.get("language", "en"),
        domain=args.get("domain"),
        output_locale=args.get("output_locale"),
        operating_point=args.get("operating_point", "standard"),
        enable_partials=True if args.get("enable_partials", False) else None,
        enable_entities=True if args.get("enable_entities", False) else None,
        max_delay=args.get("max_delay"),
        max_delay_mode=args.get("max_delay_mode"),
        diarization=args.get("diarization"),
        speaker_change_sensitivity=args.get("speaker_change_sensitivity"),
        speaker_diarization_sensitivity=args.get("speaker_diarization_sensitivity"),
    )

    if args.get("additional_vocab_file"):
        additional_vocab = parse_additional_vocab(args["additional_vocab_file"])
        config["additional_vocab"] = additional_vocab
        LOGGER.info(
            "Using additional vocab from file %s", args["additional_vocab_file"]
        )

    if args.get("additional_vocab"):
        if not config.get("additional_vocab"):
            config["additional_vocab"] = args["additional_vocab"]
        else:
            config["additional_vocab"].extend(args["additional_vocab"])
        LOGGER.info("Using additional vocab from args %s", args["additional_vocab"])

    if (
        args.get("punctuation_permitted_marks") is not None
        or args.get("punctuation_sensitivity") is not None
    ):
        config["punctuation_overrides"] = {}

        if args.get("punctuation_permitted_marks") is not None:
            config["punctuation_overrides"]["permitted_marks"] = args[
                "punctuation_permitted_marks"
            ].split()

        if args.get("punctuation_sensitivity") is not None:
            config["punctuation_overrides"]["sensitivity"] = args[
                "punctuation_sensitivity"
            ]

    if args.get("speaker_diarization_max_speakers") is not None:
        max_speakers = args.get("speaker_diarization_max_speakers")
        config["speaker_diarization_config"] = RTSpeakerDiarizationConfig(
            max_speakers=max_speakers
        )

    if args.get("speaker_diarization_sensitivity") is not None:
        speaker_sensitivity = args.get("speaker_diarization_sensitivity")
        config["speaker_diarization_config"] = BatchSpeakerDiarizationConfig(
            speaker_sensitivity=speaker_sensitivity
        )

    if args.get("channel_diarization_labels") is not None:
        labels_str = args.get("channel_diarization_labels")
        config["channel_diarization_labels"] = labels_str

    if args["mode"] == "rt":
        # pylint: disable=unexpected-keyword-arg
        return TranscriptionConfig(**config)
    # pylint: disable=unexpected-keyword-arg
    return BatchTranscriptionConfig(**config)


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
    api,
    transcripts,
    enable_partials=False,
    debug_handlers_too=False,
    speaker_change_token=False,
    print_json=False,
):
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
    """
    if debug_handlers_too:
        api.add_event_handler(
            ServerMessageType.AudioAdded, lambda *args: print_symbol("-")
        )
        api.add_event_handler(
            ServerMessageType.AddPartialTranscript, lambda *args: print_symbol(".")
        )
        api.add_event_handler(
            ServerMessageType.AddTranscript, lambda *args: print_symbol("|")
        )
        api.add_middleware(ClientMessageType.AddAudio, lambda *args: print_symbol("+"))

    def partial_transcript_handler(message):
        # "\n" does not appear in partial transcripts
        if print_json:
            print(json.dumps(message))
            return
        plaintext = speechmatics.adapters.convert_to_txt(
            message["results"],
            api.transcription_config.language,
            language_pack_info=api.get_language_pack_info(),
            speaker_labels=True,
            speaker_change_token=speaker_change_token,
        )
        if plaintext:
            print(plaintext, end="\r", file=sys.stderr)

    def transcript_handler(message):
        transcripts.json.append(message)
        if print_json:
            print(json.dumps(message))
            return
        plaintext = speechmatics.adapters.convert_to_txt(
            message["results"],
            api.transcription_config.language,
            language_pack_info=api.get_language_pack_info(),
            speaker_labels=True,
            speaker_change_token=speaker_change_token,
        )
        if plaintext:
            print(plaintext)
        transcripts.text += plaintext

    def end_of_transcript_handler(_):
        if enable_partials:
            print("\n", file=sys.stderr)

    api.add_event_handler(
        ServerMessageType.AddPartialTranscript, partial_transcript_handler
    )
    api.add_event_handler(ServerMessageType.AddTranscript, transcript_handler)
    api.add_event_handler(ServerMessageType.EndOfTranscript, end_of_transcript_handler)


def join_words(words, language="en"):
    """
    Joins a list of words with a language specific separator. Because not all
    languages use the standard English white-space between words.

    :param words: List of words
    :type words: List[str]

    :param language: Language code
    :type language: str

    :return: Words joined with a language-specific separator.
    :rtype: str
    """
    if language in {"ja", "cmn"}:
        separator = ""
    else:
        separator = " "
    return separator.join(words)


def submit_job_and_wait(
    connection_settings: ConnectionSettings,
    audio: Union[Tuple[str, bytes], str, os.PathLike],
    transcription_config: Union[
        Dict[str, Any], BatchTranscriptionConfig, str, os.PathLike
    ],
    transcription_format: str = "txt",
) -> str:
    """
    Submit a job, waiting for response.
    This is the ``batch transcribe`` command.

    :param connection_settings: Settings for API connection.
    :type connection_settings: speechmatics.models.ConnectionSettings

    :param audio: Audio file path or tuple of filename and bytes
    :type audio: os.Pathlike | str | Tuple[str, bytes]

    :param transcription_config: Configuration for the transcription.
    :type transcription_config:
        Dict[str, Any] | speechmatics.models.BatchTranscriptionConfig | str

    :param transcription_format: Format of transcript. Defaults to txt.
        Valid options are json-v2, txt, srt. json is accepted as an
        alias for json-v2.
    :type format: str

    :return: transcript in txt format
    :rtype: str
    """
    with BatchClient(connection_settings) as client:
        job_id = client.submit_job(audio, transcription_config)
        print(f"Job submission successful. ID: {job_id} . Waiting for completion")
        return client.wait_for_completion(job_id, transcription_format)


def main(args=None):
    """
    Main entrypoint.

    :param args: command-line arguments; defaults to None in which
            case arguments will retrieved from `sys.argv` (this is useful
            mainly for unit tests).
    :type args: List[str]
    """
    if not args:
        args = vars(parse_args())

    mode = args["mode"]

    logging.basicConfig(level=get_log_level(args["verbose"]))
    LOGGER.info("Args: %s", args)

    if mode == "rt":
        if not args["command"]:
            LOGGER.error("No command specified")
            args = vars(parse_args([mode, "-h"]))
        rt_main(args)
    elif mode == "batch":
        if not args["command"]:
            LOGGER.error("No command specified")
            args = vars(parse_args([mode, "-h"]))
        batch_main(args)
    else:
        # Not clear which help to show, so let's exit, but list the valid modes.
        LOGGER.error("Usage: speechmatics [rt|batch] [command]")
        raise SystemExit(
            f"Unknown mode: {mode}, mode must be one of 'rt' (realtime) or 'batch'"
        )


def rt_main(args):
    """Main dispatch for "rt" mode commands.

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    api = WebsocketClient(get_connection_settings(args))

    if args["url"].lower().startswith("ws://") and args["ssl_mode"] != "none":
        raise SystemExit(
            f"ssl_mode '{args['ssl_mode']}' is incompatible with"
            "protocol 'ws'. Use 'wss' instead."
        )
    if args["url"].lower().startswith("wss://") and args["ssl_mode"] == "none":
        raise SystemExit(
            "ssl_mode 'none' is incompatible with protocol 'wss'." "Use 'ws' instead."
        )

    transcripts = Transcripts(text="", json=[])
    add_printing_handlers(
        api,
        transcripts,
        enable_partials=args["enable_partials"],
        debug_handlers_too=args["debug"],
        speaker_change_token=args["speaker_change_token"],
        print_json=args["print_json"],
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


def batch_main(args):
    """Main dispatch for "batch" command set

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    command = args["command"]
    with BatchClient(get_connection_settings(args)) as batch_client:
        if command == "transcribe":
            for filename in args["files"]:
                print(f"Processing {filename}\n==========")
                print(
                    submit_job_and_wait(
                        connection_settings=get_connection_settings(args),
                        audio=filename,
                        transcription_config=get_transcription_config(args),
                        transcription_format=args["output_format"],
                    )
                )
                print(f"==========\n{filename} completed!\n==========")
        elif command == "submit":
            for filename in args["files"]:
                job_id = batch_client.submit_job(
                    filename, get_transcription_config(args)
                )
                print(f"Submitted {filename} successfully, job ID: {job_id}")
        elif command == "get-results":
            print(
                batch_client.get_job_result(
                    job_id=args["job_id"], transcription_format=args["output_format"]
                )
            )
        elif command == "list-jobs":
            print(batch_client.list_jobs())
        elif command == "delete":
            print(batch_client.delete_job(args["job_id"], args["force_delete"]))
        elif command == "job-status":
            print(batch_client.check_job_status(args["job_id"]))


# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
def parse_args(args=None):
    """
    Parses command-line arguments.

    :param args: List of arguments to parse.
    :type args: (List[str], optional)

    :return: The set of arguments provided along with their values.
    :rtype: Namespace
    """

    parser = argparse.ArgumentParser(description="CLI for Speechmatics products.")
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
        "--debug",
        default=False,
        action="store_true",
        help=(
            "Prints useful symbols to represent the messages on the wire. "
            "Symbols are printed to STDERR, use only when STDOUT is "
            "redirected to a file."
        ),
    )

    # Parsers for shared arguments.
    # Parent parser for commands involving files
    file_parser = argparse.ArgumentParser(add_help=False)
    file_parser.add_argument(
        "files", metavar="FILEPATHS", type=str, nargs="+", help="File(s) to process."
    )

    # Parent parser for shared connection parameters
    connection_parser = argparse.ArgumentParser(add_help=False)
    connection_parser.add_argument(
        "--url",
        type=str,
        required=True,
        help=(
            "Websocket for RT or for batch API URL (e.g. wss://192.168.8.12:9000/ "
            "or https://trial.asr.api.speechmatics.com/v2 respectively)."
        ),
    )
    connection_parser.add_argument(
        "--auth-token",
        type=str,
        help=(
            "Pre-shared authentication token to authorize the client."
            "Applies to Speechmatics SaaS products."
        ),
    )
    connection_parser.add_argument(
        "--ssl-mode",
        default="regular",
        choices=["regular", "insecure", "none"],
        help=(
            "Use a preset configuration for the SSL context. With `regular` "
            "mode a valid certificate is expected. With `insecure` mode"
            " a self signed certificate is allowed."
            " With `none` then SSL is not used."
        ),
    )
    connection_parser.add_argument(
        "--generate-temp-token",
        default=None,
        action="store_true",
        help=(
            "Automatically generate a temporary token for authentication."
            "Non-enterprise customers must set this to True."
            "Enterprise customers should set this to False."
        ),
    )

    # Parent parser for shared params related to building a job config
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--lang",
        "--language",
        dest="language",
        type=str,
        default="en",
        help="Language (ISO 639-1 code, e.g. en, fr, de).",
    )
    config_parser.add_argument(
        "--operating-point",
        choices=["standard", "enhanced"],
        help=(
            "Selects the acoustic model configuration. "
            '"enhanced" is more computationally expensive than "standard" but '
            "should result in a more accurate transcript."
        ),
    )

    config_parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Optionally request a specialized language pack, e.g. 'finance'",
    )

    config_parser.add_argument(
        "--output-locale",
        metavar="LOCALE",
        type=str,
        default=None,
        help="Locale of the output of transcripts. eg. en-US.",
    )
    config_parser.add_argument(
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
    config_parser.add_argument(
        "--additional-vocab-file",
        metavar="VOCAB_FILEPATH",
        type=str,
        help="File with additional vocab in JSON format.",
    )
    config_parser.add_argument(
        "--punctuation-permitted-marks",
        type=str,
        default=None,
        help=(
            "Space separated list of permitted punctuation marks for advanced punctuation."
        ),
    )
    config_parser.add_argument(
        "--enable-entities",
        default=False,
        action="store_true",
        help=(
            "Whether to output additional information about recognised"
            "entity classes (JSON output only)."
        ),
    )

    # Parent parser for output type
    output_format_parser = argparse.ArgumentParser(add_help=False)
    output_format_parser.add_argument(
        "--output-format",
        default="txt",
        choices=["txt", "json", "json-v2", "srt"],
        type=str,
        required=False,
        help="Transcript output format.",
    )

    # Parent parser for batch diarization argument
    batch_diarization_parser = argparse.ArgumentParser(add_help=False)
    batch_diarization_parser.add_argument(
        "--speaker-diarization-sensitivity",
        type=float,
        help="The sensitivity of the speaker detection. Default is 0.5 .",
    )
    batch_diarization_parser.add_argument(
        "--diarization",
        choices=["none", "speaker", "channel", "channel_and_speaker_change"],
        help="Which type of diarization to use.",
    )

    batch_diarization_parser.add_argument(
        "--channel-diarization-labels",
        nargs="+",
        help=(
            "Add your own speaker or channel labels to the transcript. "
            "Example usage: --channel-diarization-labels label1 label2"
        ),
    )

    # Parent parser for job_id argument
    job_id_parser = argparse.ArgumentParser(add_help=False)
    job_id_parser.add_argument("--job-id", type=str, required=True, help="Job ID.")

    # Parent parser for RT transcribe arguments
    rt_transcribe_command_parser = argparse.ArgumentParser(add_help=False)
    rt_transcribe_command_parser.add_argument(
        "--enable-partials",
        default=False,
        action="store_true",
        help=(
            "Whether to return partial transcripts which can be updated by later,"
            "final transcripts."
        ),
    )

    rt_transcribe_command_parser.add_argument(
        "--punctuation-sensitivity",
        type=float,
        help="Sensitivity level for advanced punctuation.",
    )
    rt_transcribe_command_parser.add_argument(
        "--speaker-diarization-max-speakers",
        type=int,
        help="Enforces the maximum number of speakers allowed in a single audio stream. Min: 2, Max: 20, Default: 20.",
    )
    rt_transcribe_command_parser.add_argument(
        "--speaker-change-sensitivity",
        type=float,
        help="Sensitivity level for speaker change.",
    )
    rt_transcribe_command_parser.add_argument(
        "--speaker-change-token",
        default=False,
        action="store_true",
        help="Shows a <sc> token where a speaker change was detected.",
    )
    rt_transcribe_command_parser.add_argument(
        "--max-delay",
        type=float,
        help="Maximum acceptable delay before sending a piece of transcript.",
    )
    rt_transcribe_command_parser.add_argument(
        "--max-delay-mode",
        default="flexible",
        choices=["fixed", "flexible"],
        type=str,
        help=(
            "How to interpret the max-delay size if speech is in"
            "the middle of an unbreakable entity like a number."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--raw",
        metavar="ENCODING",
        type=str,
        help=(
            "Indicate that the input audio is raw, provide the encoding"
            "of this raw audio, eg. pcm_f32le."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--sample-rate",
        type=int,
        default=44_100,
        help="The sample rate in Hz of the input audio, if in raw format.",
    )
    rt_transcribe_command_parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024 * 4,
        help=(
            "How much audio data, in bytes, to send to the server in each "
            "websocket message. Larger values can increase latency, but "
            "values which are too small create unnecessary overhead."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--buffer-size",
        default=512,
        type=int,
        help=(
            "Maximum number of messages to send before waiting for"
            "acknowledgements from the server."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--print-json",
        default=False,
        action="store_true",
        help=(
            "Print the JSON partial & final transcripts received rather than "
            "plaintext messages."
        ),
    )

    rt_transcribe_command_parser.add_argument(
        "--diarization",
        choices=["none", "speaker", "speaker_change"],
        help="Which type of diarization to use.",
    )

    # Build our actual parsers.
    mode_subparsers = parser.add_subparsers(title="Mode", dest="mode")

    # Parsers specific to rt mode commands.

    rt_parser = mode_subparsers.add_parser("rt", help="Real-time commands")
    rt_subparsers = rt_parser.add_subparsers(title="Commands", dest="command")
    rt_subparsers.add_parser(
        "transcribe",
        parents=[
            rt_transcribe_command_parser,
            file_parser,
            connection_parser,
            config_parser,
        ],
    )

    # Parsers specific to batch mode commands
    batch_parser = mode_subparsers.add_parser("batch", help="Batch commands")
    batch_subparsers = batch_parser.add_subparsers(title="Commands", dest="command")

    batch_subparsers.add_parser(
        "transcribe",
        parents=[
            file_parser,
            connection_parser,
            config_parser,
            output_format_parser,
            batch_diarization_parser,
        ],
        help="Transcribe one or more audio files using batch mode, while waiting for results.",
    )

    batch_subparsers.add_parser(
        "submit",
        parents=[
            file_parser,
            connection_parser,
            config_parser,
            output_format_parser,
            batch_diarization_parser,
        ],
        help="Submit one or more files for transcription.",
    )

    batch_subparsers.add_parser(
        "list-jobs",
        parents=[connection_parser],
        help="Retrieve json of last 100 jobs submitted within the last 7 days for the SaaS "
        "or all of the jobs for the batch appliance",
    )

    batch_subparsers.add_parser(
        "get-results",
        parents=[connection_parser, output_format_parser, job_id_parser],
        help="Retrieve results of a transcription job.",
    )

    batch_delete_parser = batch_subparsers.add_parser(
        "delete",
        parents=[connection_parser, output_format_parser, job_id_parser],
        help="Delete the results of a transcription job.",
    )
    batch_delete_parser.add_argument(
        "--force",
        default=False,
        action="store_true",
        dest="force_delete",
        help="Force deletion of a running job",
    )

    batch_subparsers.add_parser(
        "job-status",
        parents=[connection_parser, job_id_parser],
        help="Retrieve status of a transcription job.",
    )

    # Parser for the "transcribe" command uses only RT.
    mode_subparsers.add_parser(
        "transcribe",
        parents=[
            rt_transcribe_command_parser,
            file_parser,
            connection_parser,
            config_parser,
        ],
        help="Real-time commands. RETAINED FOR LEGACY COMPATIBILITY.",
    )

    parsed_args = parser.parse_args(args=args)

    # Fix up args for transcribe command
    if parsed_args.mode == "transcribe":
        parsed_args.command = "transcribe"

        if urlparse(parsed_args.url).scheme in ["ws", "wss"]:
            parsed_args.mode = "rt"
        else:
            LOGGER.error(
                "speechmatics [transcribe] mode is used only with RT for legacy compatibility, not batch."
            )
            args = vars(parse_args(["batch", "-h"]))

    return parsed_args


if __name__ == "__main__":
    main()
