# (c) 2022, Cantab Research Ltd.
"""
Parsers used by the CLI to handle CLI arguments
"""
import argparse
import logging
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)


class kvdictAppendAction(argparse.Action):
    """
    argparse action to split an argument into KEY=VALUE form
    on the first = and append to a dictionary.
    """

    def __call__(self, parser, args, values, option_string=None):
        for pair in values:
            try:
                (k, v) = pair.split("=", 2)
            except ValueError:
                raise argparse.ArgumentError(
                    self, f'could not parse argument "{pair}" as k=v format'
                )
            d = getattr(args, self.dest) or {}
            d[k] = v
            setattr(args, self.dest, d)


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


# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
def get_arg_parser():
    """
    Creates a command-line argument parser objct

    :return: The argparser object with all commands and subcommands.
    :rtype: argparse.ArgumentParser
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
    parser.add_argument(
        "--ctrl",
        type=str,
        help="Speechmatics internal use.",
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
        help=(
            "Websocket for RT or for batch API URL (e.g. wss://192.168.8.12:9000/ "
            "or https://asr.api.speechmatics.com/v2 respectively)."
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
            "Enterprise customers should set this to False."
        ),
    )
    connection_parser.add_argument(
        "--profile",
        default="default",
        type=str,
        help=(
            "Determines the local config toml profile to use."
            "Profiles can be used to maintain multiple different user accounts and setups locally."
        ),
    )

    # Parent parser for shared params related to building a job config
    config_parser = argparse.ArgumentParser(add_help=False)

    config_parser.add_argument(
        "--config-file",
        dest="config_file",
        type=str,
        default=None,
        help="Read the transcription config from a file."
        " If you provide this, all other config options work as overrides.",
    )
    config_parser.add_argument(
        "--lang",
        "--language",
        dest="language",
        type=str,
        default=None,
        help="Language (ISO 639-1 code, e.g. en, fr, de).",
    )
    config_parser.add_argument(
        "--volume-threshold",
        dest="volume_threshold",
        type=float,
        default=None,
        help=("Filter out quiet audio which falls below this threshold (0.0-100.0)"),
    )
    config_parser.add_argument(
        "--remove-disfluencies",
        default=None,
        action="store_true",
        required=False,
        help=("Removes words tagged as disfluency."),
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
            "Space-separated list of permitted punctuation marks for advanced punctuation."
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
    config_parser.add_argument(
        "--translation-langs",
        "--translation-languages",
        dest="translation_target_languages",
        type=str,
        default=None,
        help=("Comma-separated list of languages to translate the transcription into"),
    )
    config_parser.add_argument(
        "--langid-langs",
        "--langid-languages",
        dest="langid_expected_languages",
        type=str,
        default=None,
        help=("Comma-separated list of expected languages for language identification"),
    )

    # Parent parser for batch summarize argument
    batch_summarization_parser = argparse.ArgumentParser(add_help=False)
    batch_summarization_parser.add_argument(
        "--summarize",
        dest="summarize",
        action="store_true",
        default=False,
        help="Whether to generate transcript summarization",
    )
    batch_summarization_parser.add_argument(
        "--summary-content-type",
        dest="content_type",
        default=None,
        choices=["informative", "conversational", "auto"],
        type=str,
        required=False,
    )
    batch_summarization_parser.add_argument(
        "--summary-length",
        dest="summary_length",
        default=None,
        choices=["brief", "detailed"],
        type=str,
        required=False,
    )
    batch_summarization_parser.add_argument(
        "--summary-type",
        dest="summary_type",
        default=None,
        choices=["paragraphs", "bullets"],
        type=str,
        required=False,
    )

    # Parent parser for batch sentiment-analysis argument
    batch_sentiment_analysis_parser = argparse.ArgumentParser(add_help=False)
    batch_sentiment_analysis_parser.add_argument(
        "--sentiment-analysis",
        dest="sentiment_analysis",
        action="store_true",
        default=False,
        help="Perform sentiment analysis on the transcript",
    )

    # Parent parser for batch topic-detection argument
    batch_topic_detection_parser = argparse.ArgumentParser(add_help=False)
    batch_topic_detection_parser.add_argument(
        "--detect-topics",
        dest="detect_topics",
        action="store_true",
        default=False,
        help="Whether to detect topics in transcript",
    )
    batch_topic_detection_parser.add_argument(
        "--topics",
        dest="topics",
        default=None,
        type=str,
        required=False,
        help="Comma-separated list of topics for topic detection",
    )

    # Parent parser for batch auto-chapters argument
    batch_auto_chapters_parser = argparse.ArgumentParser(add_help=False)
    batch_auto_chapters_parser.add_argument(
        "--detect-chapters",
        dest="detect_chapters",
        action="store_true",
        default=False,
        help="Whether to detect chapters on the transcript",
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
        "--streaming-mode",
        default=False,
        action="store_true",
        help="Whether to run the engine in streaming mode. Internal Speechmatics use only.",
    )
    rt_transcribe_command_parser.add_argument(
        "--enable-partials",
        default=False,
        action="store_true",
        help=(
            "Whether to return partials for both transcripts and translation which can be updated by later,"
            "final transcripts."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--enable-transcription-partials",
        default=False,
        action="store_true",
        help=(
            "Whether to return partial transcripts which can be updated by later,"
            "final transcripts."
        ),
    )
    rt_transcribe_command_parser.add_argument(
        "--enable-translation-partials",
        default=False,
        action="store_true",
        help=(
            "Whether to return partial translation which can be updated by later,"
            "final translation."
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

    rt_transcribe_command_parser.add_argument(
        "--audio-events",
        action="store_true",
        help="Enable audio event detection and print events in square-brackets to the console, e.g. [MUSIC]",
    )
    rt_transcribe_command_parser.add_argument(
        "--event-types",
        default=None,
        type=str,
        required=False,
        help="Comma-separated list of whitelisted event types for audio events.",
    )
    rt_transcribe_command_parser.add_argument(
        "--extra-headers",
        default=dict(),
        nargs="+",
        action=kvdictAppendAction,
        metavar="KEY=VALUE",
        required=False,
        help="Adds extra headers to the websocket client",
    )

    # Parent parser for batch auto-chapters argument
    batch_audio_events_parser = argparse.ArgumentParser(add_help=False)
    batch_audio_events_parser.add_argument(
        "--audio-events",
        action="store_true",
        help="Enable audio event detection, "
        "will include `audio_events` and `audio_event_summary` keys in output (JSON only)",
    )
    batch_audio_events_parser.add_argument(
        "--event-types",
        default=None,
        type=str,
        required=False,
        help="Comma-separated list of whitelisted event types for audio events.",
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
        help="Transcribe an audio file or stream in real time and output the results to the console.",
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
            batch_summarization_parser,
            batch_sentiment_analysis_parser,
            batch_topic_detection_parser,
            batch_auto_chapters_parser,
            batch_audio_events_parser,
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
            batch_summarization_parser,
            batch_sentiment_analysis_parser,
            batch_topic_detection_parser,
            batch_auto_chapters_parser,
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

    # Parser for config processes setting toml config
    cli_config_parser = mode_subparsers.add_parser(
        "config",
        help="Config commands. Used to handle local config.",
    )
    cli_config_subparsers = cli_config_parser.add_subparsers(
        title="commands", dest="command"
    )
    cli_set_config_parser = cli_config_subparsers.add_parser(
        "set", help="Set config for the local CLI environment."
    )
    cli_set_config_parser.add_argument(
        "--auth-token", type=str, help="Auth token to use as default for all requests."
    )
    cli_set_config_parser.add_argument(
        "--realtime-url",
        "--rt-url",
        type=str,
        dest="realtime_url",
        help="Default URL to use for RT transcription. Overriden by the --url flag.",
    )
    cli_set_config_parser.add_argument(
        "--batch-url",
        type=str,
        help="Default URL to use for Batch transcription. Overriden by the --url flag.",
    )
    cli_set_config_parser.add_argument(
        "--generate-temp-token",
        action="store_true",
        help="Sets generate_temp_token to true in the config file."
        "This will set the --generate-temp-token to true globally wherever it is a valid command line flag.",
    )
    cli_set_config_parser.add_argument(
        "--profile",
        type=str,
        default="default",
        help="Specifies the profile to set the config for."
        "Profiles can be used to maintain multiple different sets of config locally.",
    )
    cli_unset_config_parser = cli_config_subparsers.add_parser(
        "unset", help="Remove specified config values from the CLI config file."
    )
    cli_unset_config_parser.add_argument(
        "--auth-token",
        action="store_true",
        help="If flag is set, removes the auth token value from the config file.",
    )
    cli_unset_config_parser.add_argument(
        "--generate-temp-token",
        action="store_true",
        help="If flag is set, removes the generate temp token value from the config file.",
    )
    cli_unset_config_parser.add_argument(
        "--profile",
        type=str,
        default="default",
        help="Specifies the profile to unset the config for."
        "Profiles can be used to maintain multiple different sets of config locally.",
    )
    cli_unset_config_parser.add_argument(
        "--realtime-url",
        "--rt-url",
        dest="realtime_url",
        action="store_true",
        help="Remove the default URL to use for RT transcription.",
    )
    cli_unset_config_parser.add_argument(
        "--batch-url",
        action="store_true",
        help="Remove the default URL to use for Batch transcription.",
    )
    return parser


def parse_args(args=None):
    """
    Parses command-line arguments.

    :param args: List of arguments to parse.
    :type args: (List[str], optional)

    :return: The set of arguments provided along with their values.
    :rtype: Namespace
    """
    parser = get_arg_parser()

    parsed_args = parser.parse_args(args=args)

    # Fix up args for transcribe command
    if parsed_args.mode == "transcribe":
        parsed_args.command = "transcribe"

        if urlparse(parsed_args.url).scheme in ["ws", "wss"] or parsed_args.url is None:
            parsed_args.mode = "rt"
        else:
            LOGGER.error(
                "speechmatics [transcribe] mode is used only with RT for legacy compatibility, not batch."
            )
            args = vars(parse_args(["batch", "-h"]))

    return parsed_args
