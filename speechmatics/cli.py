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
from dataclasses import dataclass
from socket import gaierror
from typing import Any, Dict, List

import httpx
import toml
from websockets.exceptions import WebSocketException

import speechmatics.adapters
from speechmatics.batch_client import BatchClient
from speechmatics.cli_parser import parse_args
from speechmatics.client import WebsocketClient
from speechmatics.config import read_config_from_home
from speechmatics.constants import BATCH_SELF_SERVICE_URL, RT_SELF_SERVICE_URL
from speechmatics.exceptions import JobNotFoundException, TranscriptionError
from speechmatics.helpers import _process_status_errors
from speechmatics.models import (
    AudioEventsConfig,
    AudioSettings,
    AutoChaptersConfig,
    BatchLanguageIdentificationConfig,
    BatchSpeakerDiarizationConfig,
    BatchTranscriptionConfig,
    ClientMessageType,
    ConnectionSettings,
    RTSpeakerDiarizationConfig,
    RTTranslationConfig,
    ServerMessageType,
    SentimentAnalysisConfig,
    SummarizationConfig,
    TopicDetectionConfig,
    TranscriptionConfig,
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
    url = args.get("url")

    stored_config = read_config_from_home(args.get("profile", "default"))
    if stored_config is not None:
        if auth_token is None and stored_config.get("auth_token") is not None:
            auth_token = stored_config["auth_token"]
        if (
            generate_temp_token is None
            and stored_config.get("generate_temp_token") is not None
        ):
            generate_temp_token = stored_config["generate_temp_token"]

        if url is None and args.get("mode") == "batch" and "batch_url" in stored_config:
            url = stored_config.get("batch_url")
        if url is None and args.get("mode") == "rt" and "realtime_url" in stored_config:
            url = stored_config.get("realtime_url")

    if url is None:
        if args.get("mode") == "batch":
            url = BATCH_SELF_SERVICE_URL
        else:
            url = f"{RT_SELF_SERVICE_URL}/{lang.strip()}"

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


def get_transcription_config(
    args,
):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
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
        config: Dict[str, Any] = {"language": "en"}

    # transcription_config is flattened in the BatchTranscriptionConfig,
    # so the config entry from JSON must be flattened here, otherwise the JSON entry would be ignored
    if config.get("transcription_config"):
        config.update(config.pop("transcription_config"))

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
        "streaming_mode",
        "enable_partials",
        "enable_entities",
        "enable_translation_partials",
        "enable_transcription_partials",
    ]:
        config[option] = True if args.get(option) else config.get(option)

    if args.get("volume_threshold") is not None:
        config["audio_filtering_config"] = {
            "volume_threshold": args.get("volume_threshold")
        }

    if args.get("remove_disfluencies") is not None:
        config["transcript_filtering_config"] = {}
        config["transcript_filtering_config"]["remove_disfluencies"] = args.get(
            "remove_disfluencies"
        )

    if args.get("ctrl"):
        LOGGER.warning(f"Using internal dev control command: {args['ctrl']}")
        config["ctrl"] = json.loads(args["ctrl"])

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

    translation_config = config.get("translation_config", {})
    args_target_languages = args.get("translation_target_languages")
    if translation_config or args_target_languages:
        enable_partials = (
            args.get("enable_partials", False)
            or args.get("enable_translation_partials", False)
            or translation_config.get("enable_partials", False)
        )
        target_languages = (
            args_target_languages.split(",")
            if args_target_languages
            else translation_config.get("target_languages")
        )
        config["translation_config"] = RTTranslationConfig(
            target_languages=target_languages,
            enable_partials=enable_partials,
        )

    if args.get("langid_expected_languages") is not None:
        langid_expected_languages = args.get("langid_expected_languages")
        config["language_identification_config"] = BatchLanguageIdentificationConfig(
            expected_languages=langid_expected_languages.split(",")
        )

    # request summarization from config file
    file_summarization_config = config.get("summarization_config", None)
    # request summarization from cli
    args_summarization = args.get("summarize")
    if args_summarization or file_summarization_config is not None:
        summarization_config = SummarizationConfig()
        content_type = args.get(
            "content_type", file_summarization_config.get("content_type")
        )
        if content_type:
            summarization_config.content_type = content_type
        summary_length = args.get(
            "summary_length", file_summarization_config.get("summary_length")
        )
        if summary_length:
            summarization_config.summary_length = summary_length
        summary_type = args.get(
            "summary_type", file_summarization_config.get("summary_type")
        )
        if summary_type:
            summarization_config.summary_type = summary_type
        config["summarization_config"] = summarization_config

    sentiment_analysis_config = config.get("sentiment_analysis_config", None)
    args_sentiment_analysis = args.get("sentiment_analysis")
    if args_sentiment_analysis or sentiment_analysis_config is not None:
        config["sentiment_analysis_config"] = SentimentAnalysisConfig()

    file_topic_detection_config = config.get("topic_detection_config", None)
    args_topic_detection = args.get("detect_topics")
    if args_topic_detection or file_topic_detection_config is not None:
        topic_detection_config = TopicDetectionConfig()
        topics = args.get("topics", file_topic_detection_config.get("topics"))
        if topics:
            topic_detection_config.topics = topics
        config["topic_detection_config"] = topic_detection_config

    auto_chapters_config = config.get("auto_chapters_config", None)
    args_auto_chapters = args.get("detect_chapters")
    if args_auto_chapters or auto_chapters_config is not None:
        config["auto_chapters_config"] = AutoChaptersConfig()

    audio_events_config = config.get("audio_events_config", None)
    arg_audio_events = args.get("audio_events", False)
    if audio_events_config is not None or arg_audio_events:
        event_types = None
        if audio_events_config and audio_events_config.get("types"):
            event_types = audio_events_config.get("types")
        if args.get("event_types"):
            event_types = str(args.get("event_types")).split(",")
        config["audio_events_config"] = AudioEventsConfig(event_types)

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


# pylint: disable=too-many-arguments,too-many-statements
def add_printing_handlers(
    api,
    transcripts,
    enable_partials=False,
    enable_transcription_partials=False,
    enable_translation_partials=False,
    debug_handlers_too=False,
    speaker_change_token=False,
    print_json=False,
    translation_config=None,
):
    """
    Adds a set of handlers to the websocket client which print out transcripts
    as they are received. This includes partials if they are enabled.

    Args:
        api (speechmatics.client.WebsocketClient): Client instance.
        transcripts (Transcripts): Allows the transcripts to be concatenated to
            produce a final result.
        enable_partials (bool, optional): Whether partials are enabled
            for both transcription and translation.
        enable_transcription_partials (bool, optional): Whether partials are enabled
            for transcription only.
        enable_translation_partials (bool, optional): Whether partials are enabled
            for translation only.
        debug_handlers_too (bool, optional): Whether to enable 'debug'
            handlers that print out an ASCII symbol representing messages being
            received and sent.
        speaker_change_token (bool, optional): Whether to explicitly include a
            speaker change token '<sc>' in the output to indicate speaker
            changes.
        print_json (bool, optional): Whether to print json transcript messages.
        translation_config (TranslationConfig, optional): Translation config with target languages.
    """
    escape_seq = "\33[2K" if sys.stdout.isatty() else ""

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
            sys.stderr.write(f"{escape_seq}{plaintext}\r")

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
            sys.stdout.write(f"{escape_seq}{plaintext}\n")
        transcripts.text += plaintext

    def audio_event_handler(message):
        if print_json:
            print(json.dumps(message))
            return
        event_name = message["event"].get("type", "").upper()
        sys.stdout.write(f"{escape_seq}[{event_name}]\n")
        transcripts.text += f"[{event_name}] "

    def partial_translation_handler(message):
        if print_json:
            print(json.dumps(message))
            return
        # Translations for all requested languages should be available
        # but, we're only going to print one translation
        if translation_config.target_languages[0] == message["language"]:
            plaintext = speechmatics.adapters.get_txt_translation(message["results"])
            sys.stderr.write(f"{escape_seq}{plaintext}\r")

    def translation_handler(message):
        transcripts.json.append(message)
        if print_json:
            print(json.dumps(message))
            return
        # Translations for all requested languages should be available
        # but, we're only going to print one translation
        if translation_config.target_languages[0] == message["language"]:
            plaintext = speechmatics.adapters.get_txt_translation(message["results"])
            if plaintext:
                sys.stdout.write(f"{escape_seq}{plaintext}\n")
            transcripts.text += plaintext

    def end_of_transcript_handler(_):
        if enable_partials:
            print("\n", file=sys.stderr)

    api.add_event_handler(ServerMessageType.EndOfTranscript, end_of_transcript_handler)

    # print both transcription and translation messages (if json was requested)
    # print translation (if text was requested then)
    # print transcription (if text was requested without translation)

    api.add_event_handler(ServerMessageType.AudioEventStarted, audio_event_handler)
    if print_json:
        if enable_partials or enable_translation_partials:
            api.add_event_handler(
                ServerMessageType.AddPartialTranslation,
                partial_translation_handler,
            )
        api.add_event_handler(ServerMessageType.AddTranslation, translation_handler)
        if enable_partials or enable_transcription_partials:
            api.add_event_handler(
                ServerMessageType.AddPartialTranscript,
                partial_transcript_handler,
            )
        api.add_event_handler(ServerMessageType.AddTranscript, transcript_handler)
    else:
        if translation_config is not None:
            if enable_partials or enable_translation_partials:
                api.add_event_handler(
                    ServerMessageType.AddPartialTranslation,
                    partial_translation_handler,
                )
            api.add_event_handler(ServerMessageType.AddTranslation, translation_handler)
        else:
            if enable_partials or enable_transcription_partials:
                api.add_event_handler(
                    ServerMessageType.AddPartialTranscript,
                    partial_transcript_handler,
                )
            api.add_event_handler(ServerMessageType.AddTranscript, transcript_handler)


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


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def main(args=None):
    """
    Main entrypoint.

    :param args: command-line arguments; defaults to None in which
            case arguments will be retrieved from `sys.argv` (this is useful
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
    extra_headers = args.get("extra_headers")

    if settings.url.lower().startswith("ws://") and args["ssl_mode"] != "none":
        raise SystemExit(
            f"ssl_mode '{args['ssl_mode']}' is incompatible with"
            "protocol 'ws'. Use 'wss' instead."
        )
    if settings.url.lower().startswith("wss://") and args["ssl_mode"] == "none":
        raise SystemExit(
            "ssl_mode 'none' is incompatible with protocol 'wss'. Use 'ws' instead."
        )

    transcripts = Transcripts(text="", json=[])
    add_printing_handlers(
        api,
        transcripts,
        enable_partials=args["enable_partials"],
        enable_transcription_partials=args["enable_transcription_partials"],
        enable_translation_partials=args["enable_translation_partials"],
        debug_handlers_too=args["debug"],
        speaker_change_token=args["speaker_change_token"],
        print_json=args["print_json"],
        translation_config=transcription_config.translation_config,
    )

    def run(stream):
        try:
            api.run_synchronously(
                stream,
                transcription_config,
                get_audio_settings(args),
                from_cli=True,
                extra_headers=extra_headers,
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
    with BatchClient(get_connection_settings(args), from_cli=True) as batch_client:
        if command == "transcribe":
            for filename in args["files"]:
                print(f"Processing {filename}\n==========")
                job_id = batch_client.submit_job(
                    filename, get_transcription_config(args)
                )
                print(
                    f"Job submission successful. ID: {job_id} . Waiting for completion"
                )
                result = batch_client.wait_for_completion(job_id, args["output_format"])
                if args["output_format"] in ["json", "json-v2"]:
                    print(json.dumps(result, ensure_ascii=False))
                else:
                    print(result)
                print(f"==========\n{filename} completed!\n==========")
        elif command == "submit":
            for filename in args["files"]:
                job_id = batch_client.submit_job(
                    filename, get_transcription_config(args)
                )
                print(f"Submitted {filename} successfully, job ID: {job_id}")
        elif command == "get-results":
            result = batch_client.get_job_result(
                job_id=args["job_id"], transcription_format=args["output_format"]
            )
            if args["output_format"] in ["json", "json-v2"]:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(result)
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
    command = args.get("command")
    if command == "set":
        set_config(args)
    if command == "unset":
        unset_config(args)


def set_config(args):
    """
    Function which handles the config set commands, storing values in the toml file.

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    home_directory = os.path.expanduser("~")
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

    profile = args.get("profile", "default")
    if profile not in cli_config:
        cli_config[profile] = {}
    if args.get("auth_token"):
        cli_config[profile]["auth_token"] = args.get("auth_token")
    if args.get("generate_temp_token"):
        cli_config[profile]["generate_temp_token"] = True
    if args.get("batch_url"):
        cli_config[profile]["batch_url"] = args.get("batch_url")
    if args.get("realtime_url"):
        cli_config[profile]["realtime_url"] = args.get("realtime_url")

    with open(f"{home_directory}/.speechmatics/config", "w", encoding="UTF-8") as file:
        toml.dump(cli_config, file)


def unset_config(args):
    """
    Function which handles the config unset commands, removing values from the toml file.

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    home_directory = os.path.expanduser("~")
    cli_config = {"default": {}}

    if os.path.exists(f"{home_directory}/.speechmatics"):
        if os.path.exists(f"{home_directory}/.speechmatics/config"):
            with open(
                f"{home_directory}/.speechmatics/config", "r", encoding="UTF-8"
            ) as file:
                toml_string = file.read()
                cli_config = toml.loads(toml_string)

            profile = args.get("profile", "default")
            if profile not in cli_config:
                raise SystemExit(
                    f"Cannot unset config for profile {profile}. Profile does not exist."
                )
            if "auth_token" in cli_config[profile] and args.get("auth_token"):
                cli_config[profile].pop("auth_token")
            if (
                args.get("generate_temp_token")
                and "generate_temp_token" in cli_config[profile]
            ):
                cli_config[profile].pop("generate_temp_token")
            if "batch_url" in cli_config[profile] and args.get("batch_url"):
                cli_config[profile].pop("batch_url")
            if "realtime_url" in cli_config[profile] and args.get("realtime_url"):
                cli_config[profile].pop("realtime_url")

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
