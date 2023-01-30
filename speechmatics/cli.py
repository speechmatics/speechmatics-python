#!/usr/bin/env python3
# (c) 2020, Cantab Research Ltd.
"""
Command-line interface
"""

import json
import logging
import os
import ssl
import sys
from socket import gaierror

from dataclasses import dataclass
from typing import List, Dict, Union, Tuple, Any

import toml
import httpx
from websockets.exceptions import WebSocketException

import speechmatics.adapters
from speechmatics.helpers import _process_status_errors
from speechmatics.client import WebsocketClient
from speechmatics.batch_client import BatchClient
from speechmatics.exceptions import (
    TranscriptionError,
    JobNotFoundException,
)
from speechmatics.models import (
    TranscriptionConfig,
    AudioSettings,
    ClientMessageType,
    ServerMessageType,
    ConnectionSettings,
    BatchTranscriptionConfig,
    BatchSpeakerDiarizationConfig,
    RTSpeakerDiarizationConfig,
    BatchTranslationConfig,
)
from speechmatics.cli_parser import (
    parse_args,
)
from speechmatics.constants import (
    BATCH_SELF_SERVICE_URL,
    RT_SELF_SERVICE_URL,
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


def get_connection_settings(args, lang="en"):
    """
    Helper function which returns a ConnectionSettings object based on the
    command line options given to the program.

    :param args: Keyword arguments, typically from the command line.
    :type args: dict

    :return: Settings for the WebSocket connection.
    :rtype: speechmatics.models.ConnectionSettings
    """
    auth_token = args.get("auth_token")
    generate_temp_token = args.get("generate_temp_token")

    home_directory = os.path.expanduser("~")
    if os.path.exists(f"{home_directory}/.speechmatics/config"):
        cli_config = {"default": {}}
        with open(
            f"{home_directory}/.speechmatics/config", "r", encoding="UTF-8"
        ) as file:
            cli_config = toml.load(file)
        if cli_config["default"].get("auth_token") is not None and auth_token is None:
            auth_token = cli_config["default"].get("auth_token", None)
        if generate_temp_token is None:
            generate_temp_token = cli_config["default"].get("generate_temp_token")

    url = args.get("url", None)
    if url is None:
        if args.get("mode") == "batch":
            url = BATCH_SELF_SERVICE_URL
        else:
            url = f"{RT_SELF_SERVICE_URL}/{lang}"

    settings = ConnectionSettings(
        url=url,
        auth_token=auth_token,
        generate_temp_token=generate_temp_token,
    )

    if args.get("buffer_size") is not None:
        settings.message_buffer_size = args["buffer_size"]

    if args.get("ssl_mode") == "insecure":
        settings.ssl_context.check_hostname = False
        settings.ssl_context.verify_mode = ssl.CERT_NONE
    elif args.get("ssl_mode") == "none":
        settings.ssl_context = None

    return settings


def get_transcription_config(args):  # pylint: disable=too-many-branches
    """
    Helper function which returns a TranscriptionConfig object based on the
    command line options given to the program.

    :param args: Keyword arguments probably from the command line.
    :type args: dict

    :return: Settings for the ASR engine.
    :rtype: speechmatics.models.TranscriptionConfig |
    speechmatics.models.BatchTranscriptionConfig
    """
    # First get configuration from a config file if one is provided.
    if args.get("config_file"):
        with open(args["config_file"], encoding="utf-8") as config_file:
            config = json.load(config_file)
    else:
        # Ensure "en" is the default language as to not break existing API behavior.
        config = {"language": "en"}

    # Explicit command line arguments override values from config file.
    for option in [
        "language",
        "domain",
        "output_locale",
        "operating_point",
        "max_delay",
        "max_delay_mode",
        "diarization",
        "channel_diarization_labels",
        "speaker_change_sensitivity",
        "speaker_diarization_sensitivity",
    ]:
        if args.get(option) is not None:
            config[option] = args[option]
    for option in [
        "enable_partials",
        "enable_entities",
    ]:
        config[option] = True if args.get(option) else config.get(option)

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

    if args.get("translation_target_languages") is not None:
        translation_target_languages = args.get("translation_target_languages")
        config["translation_config"] = BatchTranslationConfig(
            target_languages=translation_target_languages.split(",")
        )

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


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
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

    try:
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
        elif mode == "config":
            if not args.get("command"):
                LOGGER.error("No command specified")
                args = vars(parse_args([mode, "-h"]))
            config_main(args)
        else:
            # Not clear which help to show, so let's exit, but list the valid modes.
            LOGGER.error("Usage: speechmatics [rt|batch|config] [command]")
            raise SystemExit(
                f"Unknown mode: {mode}, mode must be one of 'rt' (realtime), 'batch' or 'config'"
            )
    except (KeyboardInterrupt, ValueError, TranscriptionError, KeyError) as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(f"{type(error).__name__}: {error}")
    except FileNotFoundError as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(
            f"FileNotFoundError: {error.strerror}: '{error.filename}'."
            + " Check to make sure the filename is spelled correctly, and that the file exists."
        )
    except JobNotFoundException as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(
            "JobNotFoundException: "
            + f"{error}. Make sure the job id you've entered is correct, and that the url is set correctly."
        )
    except httpx.HTTPStatusError as error:
        LOGGER.info(error, exc_info=True)
        _process_status_errors(error)
    except httpx.HTTPError as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(f"httpx.HTTPError: An unexpected http error occurred. {error}")
    except ConnectionResetError as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(
            f"ConnectionResetError: {error}.\n\nThe most likely reason for this is that the client "
            + "has been configured to use SSL but the server does not support SSL. "
            + "If this is the case then try using --ssl-mode=none"
        )
    except (WebSocketException, gaierror) as error:
        LOGGER.info(error, exc_info=True)
        sys.exit(
            f"WebSocketError: An unexpected error occurred in the websocket: {error}.\n\n"
            + "Check that the url and config provided is valid, "
            + "and that the language in the url matches the config.\n"
        )


def rt_main(args):
    """Main dispatch for "rt" mode commands.

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    transcription_config = get_transcription_config(args)
    settings = get_connection_settings(args, lang=transcription_config.language)
    api = WebsocketClient(settings)

    if settings.url.lower().startswith("ws://") and args["ssl_mode"] != "none":
        raise SystemExit(
            f"ssl_mode '{args['ssl_mode']}' is incompatible with"
            "protocol 'ws'. Use 'wss' instead."
        )
    if settings.url.lower().startswith("wss://") and args["ssl_mode"] == "none":
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


def config_main(args):
    """Main dispatch for "config" command set

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    home_directory = os.path.expanduser("~")
    command = args.get("command")
    if command == "set":
        cli_config = {"default": {}}
        if os.path.exists(f"{home_directory}/.speechmatics"):
            if os.path.exists(f"{home_directory}/.speechmatics/config"):
                with open(
                    f"{home_directory}/.speechmatics/config", "r", encoding="UTF-8"
                ) as file:
                    toml_string = file.read()
                    cli_config = toml.loads(toml_string)
        else:
            os.makedirs(f"{home_directory}/.speechmatics")

        if args.get("auth_token"):
            cli_config["default"]["auth_token"] = args.get("auth_token")
        if args.get("generate_temp_token"):
            cli_config["default"]["generate_temp_token"] = True

        with open(
            f"{home_directory}/.speechmatics/config", "w", encoding="UTF-8"
        ) as file:
            toml.dump(cli_config, file)

    if command == "unset":
        cli_config = {"default": {}}

        if os.path.exists(f"{home_directory}/.speechmatics"):
            if os.path.exists(f"{home_directory}/.speechmatics/config"):
                with open(
                    f"{home_directory}/.speechmatics/config", "r", encoding="UTF-8"
                ) as file:
                    toml_string = file.read()
                    cli_config = toml.loads(toml_string)

                if args.get("auth_token") and cli_config["default"].get("auth_token"):
                    cli_config["default"].pop("auth_token")
                if (
                    args.get("generate_temp_token")
                    and cli_config["default"].get("generate_temp_token") is not None
                ):
                    cli_config["default"].pop("generate_temp_token")

                with open(
                    f"{home_directory}/.speechmatics/config", "w", encoding="UTF-8"
                ) as file:
                    toml.dump(cli_config, file)
                return

        raise SystemExit(
            f"Unable to remove config. No config file stored found at {home_directory}/.speechmatics/config"
        )


if __name__ == "__main__":
    main()
