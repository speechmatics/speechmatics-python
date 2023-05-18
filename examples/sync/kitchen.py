import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from sys import exit, stderr
from textwrap import wrap

from . import sync

BLUE_BACKGROUND = "\033[48;2;84;150;250m"
GRAY_FOREGROUND = "\033[38;2;50;50;0m"
GREEN_FOREGROUND = "\033[38;2;50;255;50m"
TIME_FOREGROUND = "\033[38;2;247;69;123m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"

HIGHLIGHT_START = BLUE_BACKGROUND + GRAY_FOREGROUND
HIGHLIGHT_END = RESET


def pretty_print_search_results(rows, is_full):
    def highlight(text):
        text = text.replace(sync.HIGHLIGHT_START_MARKER, HIGHLIGHT_START)
        text = text.replace(sync.HIGHLIGHT_END_MARKER, HIGHLIGHT_END)
        return text

    def curly_quote(text):
        return (
            "\N{LEFT DOUBLE QUOTATION MARK}" + text + "\N{RIGHT DOUBLE QUOTATION MARK}"
        )

    def format_snippet(text):
        if not sys.stdout.isatty():
            return text
        width, _ = os.get_terminal_size()
        indent = "  "
        lines = wrap(
            curly_quote(text),
            width=width,
            initial_indent=indent,
            subsequent_indent=indent,
        )
        return "\n".join(map(highlight, lines))

    def format_path(path):
        cwd = Path.cwd()
        if path.is_relative_to(cwd):
            path = path.relative_to(cwd)
        parts = [UNDERLINE, GREEN_FOREGROUND, path, RESET]
        return "".join(map(str, parts))

    def format_timestamp(timestamp):
        m = timestamp // 60
        s = timestamp % 60
        return f"{TIME_FOREGROUND}{m:02.0f}:{s:04.1f}{RESET}"

    for index, row in enumerate(rows):
        path, timestamp, text, snippet = row
        print(
            "\n" if index > 0 else "",
            format_timestamp(timestamp),
            " ",
            format_path(path),
            "\n",
            format_snippet(text if is_full else snippet),
            "\n",
            sep="",
            end="",
        )


def print_raw(rows):
    for row in rows:
        print("\t".join(map(str, row)))


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument(
        "api_key",
        help="A valid API key",
    )
    parser.add_argument(
        "audio_root",
        help="The directory containing your audio files",
        type=Path,
    )
    parser.add_argument(
        "--search",
        help="Search the transcripts database for results that match the given audio directory",
        metavar="TERMS",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Don't transcribe new audio; useful when you just want to search",
    )
    parser.add_argument(
        "--full-result",
        action="store_true",
        help="Normally search results just show a transcript snippet.  This shows the full result.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print machine parseable rows",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all rows instead of using search terms",
    )

    args = parser.parse_args()
    client = sync.connect_to_api(args.api_key)
    config = dict(language="en")
    db = sync.Database()

    if not args.audio_root.exists():
        print(f"Audio root not found: {args.audio_root}", file=stderr)
        return 1

    if not args.no_sync:
        sync.sync(args.audio_root, client, config, db)

    if args.all:
        rows = sync.fetch_all(db, args.audio_root)
        print_raw(rows)
    if args.search:
        search_results = sync.search(
            db,
            args.audio_root,
            args.search,
        )
        if args.raw:
            print_raw(search_results)
        else:
            pretty_print_search_results(
                search_results,
                args.full_result,
            )


if __name__ == "__main__":
    exit(main())
