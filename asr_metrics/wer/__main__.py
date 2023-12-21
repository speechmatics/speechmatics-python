"""
Simple script to run WER analysis using Whisper normalisers
Prints results to terminal
"""
import difflib
import json
from pathlib import Path
from typing import Any, Tuple, Optional
from collections import Counter
import argparse
import pandas as pd

from jiwer import compute_measures, cer
from asr_metrics.wer.normalizers import BasicTextNormalizer, EnglishTextNormalizer


def load_file(path: Path, file_type: str) -> str:
    """
    Returns a string containing the contents of a file, given the file path
    """
    return load_text(path) if file_type == "txt" else load_sm_json(path)


def load_text(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8") as input_path:
            return input_path.read()
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Error reading file {path}: {error}. Ensure the file is UTF-8 encoded."
        )


def load_sm_json(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as input_path:
        json_transcript = json.load(input_path)

    return parse_sm_json(json_transcript)


def parse_sm_json(json_transcript: dict) -> str:
    assert (
        float(json_transcript["format"]) > 2.8
    ), "Requires JSON transcript version 2.8 or later"
    delimiter = json_transcript["metadata"]["language_pack_info"]["word_delimiter"]
    words = []

    for word in json_transcript["results"]:
        content = word["alternatives"][0]["content"]
        if word.get("attaches_to"):
            words[-1] += content
            continue
        words.append(content)

    return delimiter.join(words)


def read_dbl(path: Path) -> list[str]:
    """
    Returns a list of file path, given an input DBL file path
    """
    with open(path, "r", encoding="utf-8") as input_path:
        return input_path.readlines()


class TranscriptDiff(difflib.SequenceMatcher):
    def __init__(self, ref: list, hyp: list, join_token=" "):
        super().__init__(None, ref, hyp)

        self.endcolour = "\x1b[0m"
        self.join_token = join_token

        self.errors: dict[str, list] = {
            "insertions": [],
            "deletions": [],
            "substitutions": [],
        }

        self.colour_mapping = {
            "INSERTION": "\x1b[38;5;16;48;5;2m",
            "DELETION": "\x1b[38;5;16;48;5;1m",
            "SUBSTITUTION": "\x1b[0;30;43m",
        }
        self.ref = ref
        self.hyp = hyp
        self.diff = self.join_token.join(self.process_diff())

    def _colourise_segment(self, transcript_segment: str, colour) -> str:
        """
        Return a transcript with the ANSI escape codes attached either side
        See here: https://tforgione.fr/posts/ansi-escape-codes/
        """
        return f"{colour}{transcript_segment}{self.endcolour}"

    def process_diff(self) -> list:
        """
        Populates the error dict and returns a colourised diff between the transcripts

        Args:
            ref (list): the reference transcript
            hyp (list): the hypothesis transcript

        Returns:
            diff (list): a colourised diff between the transcripts as a list of segments
        """

        diff = []
        for opcode, ref_i, ref_j, hyp_i, hyp_j in self.get_opcodes():
            ref_segment = self.join_token.join(self.ref[ref_i:ref_j])
            hyp_segment = self.join_token.join(self.hyp[hyp_i:hyp_j])

            if opcode == "equal":
                diff.append(ref_segment)

            if opcode == "insert":
                diff.append(
                    self._colourise_segment(
                        hyp_segment, self.colour_mapping["INSERTION"]
                    )
                )
                self.errors["insertions"].append(hyp_segment)

            if opcode == "delete":
                diff.append(
                    self._colourise_segment(
                        ref_segment, self.colour_mapping["DELETION"]
                    )
                )
                self.errors["deletions"].append(ref_segment)

            if opcode == "replace":
                diff.append(
                    self._colourise_segment(
                        f"{ref_segment} -> {hyp_segment}",
                        self.colour_mapping["SUBSTITUTION"],
                    )
                )
                self.errors["substitutions"].append(f"{ref_segment} -> {hyp_segment}")

        return diff

    def print_colourised_diff(self) -> None:
        "Prints the colourised diff and error key"
        print("DIFF", end="\n\n")
        for error_type, colour in self.colour_mapping.items():
            print(self._colourise_segment(error_type, colour))
        print(self.diff, end="\n\n")

    def _print_errors_for_type(self, error_type: str, errors: list) -> None:
        """
        Prints colourised key for error type and then prints all errors in list

        Args:
            error_type (str): One of INSERTION, DELETION or SUBSTITUTION
            errors (list): Contains a list of errorneous transcript segments

        Raises:
            AssertionError if error_type is not one of INSERTION, DELETION or SUBSTITUTION
        """
        assert error_type in ["INSERTION", "DELETION", "SUBSTITUTION"]

        print(self._colourise_segment(error_type, self.colour_mapping[error_type]))

        for error in errors:
            print(error, end="\n")

    def print_errors_by_type(self) -> None:
        """
        Iterates over each type of error and prints all examples
        """
        error_types = ["INSERTION", "DELETION", "SUBSTITUTION"]
        for error_type, list_of_errors in zip(error_types, self.errors.values()):
            self._print_errors_for_type(error_type, list_of_errors)
            print("\n")


def count_errors(errors_list: list) -> list[tuple[Any, int]]:
    """
    Use Counter.most_common() to list errors by the number of times they occur

    Args:
        errors_list (list): a list of errors to be enumerated

    Returns:
        list of tuples in the form (error, number of occurances)
    """
    return Counter(errors_list).most_common()


def is_supported(file_name: str) -> bool:
    "Takes input file name, checks if file is valid"
    return file_name.endswith((".dbl", ".txt", ".json", ".json-v2"))


def run_cer(ref: str, hyp: str) -> Tuple[TranscriptDiff, dict[str, Any]]:
    """
    Run CER for input reference and hypothesis transcripts

    Args:
        ref (str): reference transcript
        hyp (str): hypothesis transcript

    Returns:
        differ (dict): instance of the TranscriptDiff class with the error dict populated
        stats (dict): a dictionary containing the CER and other stats
    """
    differ = TranscriptDiff(list(ref), list(hyp), join_token="")
    stats = cer(ref, hyp, return_dict=True)
    stats["reference length"] = len(list(ref))
    stats["accuracy"] = 1 - stats["cer"]
    return differ, stats


def run_wer(ref: str, hyp: str) -> Tuple[TranscriptDiff, dict[str, Any]]:
    """
    Run WER for a single input reference and hypothesis transcript

    Args:
        ref (str): reference transcript
        hyp (str): hypothesis transcript

    Returns:
        differ (dict): instance of the TranscriptDiff class with the error dict populated
        stats (dict): a dictionary containing the WER and other stats
    """
    differ = TranscriptDiff(ref.split(), hyp.split(), join_token=" ")
    stats = compute_measures(ref, hyp)
    stats["reference length"] = len(ref.split())
    stats["accuracy"] = 1 - stats["wer"]
    return differ, stats


def check_paths(ref_path, hyp_path) -> Tuple[list[str], list[str]]:
    """
    Returns lists of ref and hyp file paths given input paths

    Raises:
        AssertionError: if input paths do not have valid extension
        ValueError: if input paths are not of the same type
    """
    assert is_supported(ref_path) and is_supported(hyp_path)

    if ref_path.endswith(".dbl") and hyp_path.endswith(".dbl"):
        return read_dbl(ref_path), read_dbl(hyp_path)

    if ref_path.endswith(".txt") and hyp_path.endswith((".txt", ".json", ".json-v2")):
        return [ref_path], [hyp_path]

    raise ValueError("Unexpected file type. Please ensure files of the same type")


def get_wer_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--non-en", help="Indicate the language is NOT english", action="store_true"
    )
    parser.add_argument(
        "--show-normalised", help="Show the normalised transcipts", action="store_true"
    )
    parser.add_argument(
        "--transcript-type",
        help="Choose the transcript format for the hypothesis. Reference must be text.",
        choices=["json", "txt"],
        default="txt",
        type=str,
    )
    parser.add_argument(
        "--diff",
        help="Show a colourised diff between normalised transcripts",
        action="store_true",
    )
    parser.add_argument(
        "--show-errors", help="Print errors separately", action="store_true"
    )
    parser.add_argument(
        "--cer",
        help="""
        Compute Character Error Rate instead of Word Error Rate.
        Spaces are considered as characters here.
        """,
        action="store_true",
    )
    parser.add_argument(
        "--keep-disfluencies",
        help="Retain disfluencies such as 'uhhh' and 'umm'. Disfluencies will be removed otherwise.",
        action="store_true",
    )
    parser.add_argument("--csv", help="Write the results to a CSV", type=Path)
    parser.add_argument("ref_path", help="Path to the reference transcript", type=str)
    parser.add_argument("hyp_path", help="Path to the hypothesis transcript", type=str)
    return parser


def main(args: Optional[argparse.Namespace] = None):
    """
    Calls argparse to make a command line utility
    """

    if args is None:
        parser = get_wer_args(argparse.ArgumentParser())
        args = parser.parse_args()

    if args.non_en:
        normaliser = BasicTextNormalizer()
    elif args.keep_disfluencies:
        normaliser = EnglishTextNormalizer(remove_disfluencies=False)
    else:
        normaliser = EnglishTextNormalizer(remove_disfluencies=True)

    ref_files, hyp_files = check_paths(args.ref_path, args.hyp_path)
    columns = [
        "file name",
        "wer",
        "reference length",
        "substitutions",
        "deletions",
        "insertions",
    ]
    columns[1] = "cer" if args.cer else columns[1]
    results = None

    for ref, hyp in zip(ref_files, hyp_files):
        norm_ref = normaliser(load_file(ref.strip(), file_type="txt"))
        norm_hyp = normaliser(load_file(hyp.strip(), file_type=args.transcript_type))

        warning = (
            f"Reference or Hypothesis file empty. Skipping...\nRef: {ref}Hyp: {hyp}"
        )
        if len(norm_ref) == 0 or len(norm_hyp) == 0:
            print(warning)
            continue

        if args.cer is True:
            differ, stats = run_cer(norm_ref, norm_hyp)
        else:
            differ, stats = run_wer(norm_ref, norm_hyp)

        stats["file name"] = hyp

        if args.show_normalised is True:
            print("NORMALISED REFERENCE:", norm_ref, sep="\n\n", end="\n\n")
            print("NORMALISED HYPOTHESIS:", norm_hyp, sep="\n\n", end="\n\n")

        if args.diff is True:
            differ.print_colourised_diff()

        if args.show_errors is True:
            differ.print_errors_by_type()

        if results is None:
            results = pd.DataFrame(stats, columns=columns, index=[0])
            continue

        results = pd.concat(
            [results, pd.DataFrame(stats, columns=columns, index=[0])],
            ignore_index=True,
        )

    print(results.to_markdown(index=False))

    if args.csv:
        results.to_csv(args.csv, index=False)


if __name__ == "__main__":
    main()
