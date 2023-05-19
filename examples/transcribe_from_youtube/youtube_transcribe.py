import argparse
import json
import logging
from pathlib import Path

import streamlink  # pylint: disable=E0401
from speechmatics.client import WebsocketClient
from speechmatics.models import AudioSettings
from speechmatics.cli import (
    get_transcription_config,
    get_connection_settings,
    Transcripts,
    add_printing_handlers,
)

LOGGER = logging.getLogger(__name__)


def id_from_url(url: str) -> str:
    return url.split("/")[-1]


def write_history(outdir: str, transcripts: Transcripts, filename: str):
    Path(outdir).mkdir(exist_ok=True, parents=True)
    with open(Path(outdir) / (filename + ".json"), "w", encoding="utf-8") as outfile:
        json.dump(transcripts.json, outfile)
    with open(Path(outdir) / (filename + ".txt"), "w", encoding="utf-8") as outfile:
        outfile.write(transcripts.text)


def main(args):
    """Transcribe (and translate) an online video.

    :param args: arguments from parse_args()
    :type args: argparse.Namespace
    """
    args["mode"] = "rt"
    transcription_config = get_transcription_config(args)

    settings = get_connection_settings(args, lang=transcription_config.language)
    api = WebsocketClient(settings)

    transcripts = Transcripts(text="", json=[])
    add_printing_handlers(
        api,
        transcripts,
        enable_partials=transcription_config.enable_partials,
        enable_transcription_partials=transcription_config.enable_transcription_partials,
        enable_translation_partials=transcription_config.enable_translation_partials,
        translation_config=transcription_config.translation_config,
    )

    def run(stream):
        try:
            api.run_synchronously(stream, transcription_config, AudioSettings())
        except KeyboardInterrupt:
            # Gracefully handle Ctrl-C, else we get a huge stack-trace.
            LOGGER.warning("Keyboard interrupt received.")

    audio_stream = streamlink.streams(args["input_url"])["best"].open()
    run(audio_stream)

    if args.get("output_dir"):
        write_history(args["output_dir"], transcripts, id_from_url(args["input_url"]))


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-url",
        type=str,
        required=True,
        help="URL of the video to be transcribed/translated.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory in which to save the trancribed/translated content."
            "If not specified, transcription will just be printed to stdout and not saved."
        ),
    )
    parser.add_argument(
        "--language",
        dest="language",
        type=str,
        default="en",
        help="Language of the video",
    )
    parser.add_argument(
        "--translation-langs",
        "--translation-languages",
        dest="translation_target_languages",  # pylint: disable=R0801
        type=str,
        default=None,
        help="Comma-separated list of languages to translate video content into",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        help="Maximum acceptable delay before sending a piece of transcript.",
    )
    parser.add_argument(
        "--enable-partials",
        default=False,
        action="store_true",
        help=(
            "Whether to return and print partials for both transcripts and translation. Partials are not saved."
        ),
    )
    return parser


if __name__ == "__main__":
    transcription_parser = get_parser()
    parsed_args = transcription_parser.parse_args()
    main(vars(parsed_args))
