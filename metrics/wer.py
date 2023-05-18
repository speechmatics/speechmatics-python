"""
Simple script to run WER analysis using Whisper normalisers
Prints results to terminal
"""
import difflib
import csv
from typing import Any, Tuple
from collections import Counter
from argparse import ArgumentParser
from jiwer import compute_measures, cer
from metrics.normalizers import BasicTextNormalizer, EnglishTextNormalizer


def load_file(path: str) -> str:
    """
    Returns a string containing the contents of a file, given the file path
    """
    with open(path, "r", encoding="utf-8") as input_path:
        return input_path.read()


def read_dbl(path: str) -> list[str]:
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

        if len(errors) > 0:
            return None

        print(self._colourise_segment(error_type, self.colour_mapping[error_type]))
        for error in errors:
            print(error, end="\n")

        return None

    def print_errors_by_type(self) -> None:
        """
        Iterates over each type of error and prints all examples
        """
        error_types = ["INSERTION", "DELETION", "SUBSTITUTION"]
        for error_type, list_of_errors in zip(error_types, self.errors.values()):
            self._print_errors_for_type(error_type, list_of_errors)


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
    return file_name.endswith((".dbl", ".txt"))


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


def generate_csv(results, using_cer=False):
    """
    Writes results to a csv named 'results.csv'
    """
    fields = [
        "file name",
        "wer",
        "accuracy",
        "insertions",
        "deletions",
        "substitutions",
        "reference length",
    ]

    if using_cer is True:
        fields[1] = "cer"

    with open("results.csv", "w", encoding="utf-8") as results_csv:
        writer = csv.DictWriter(results_csv, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(row)


def check_paths(ref_path, hyp_path) -> Tuple[list[str], list[str]]:
    """
    Returns lists of ref and hyp file paths given input paths

    Raises:
        AssertionError: if input paths do not have same extension
    """
    assert is_supported(ref_path) and is_supported(hyp_path)

    if ref_path.endswith(".txt") and hyp_path.endswith(".txt"):
        return [ref_path], [hyp_path]
    if ref_path.endswith(".dbl") and hyp_path.endswith(".dbl"):
        return read_dbl(ref_path), read_dbl(hyp_path)

    raise ValueError("Unexpected file type. Please ensure files are .dbl or .txt files")


def main():
    """
    Calls argparse to make a command line utility
    """

    parser = ArgumentParser()
    parser.add_argument(
        "--non-en", help="Indicate the language is NOT english", action="store_true"
    )
    parser.add_argument(
        "--show-normalised", help="Show the normalised transcipts", action="store_true"
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
    parser.add_argument("--csv", help="Write the results to a CSV", action="store_true")
    parser.add_argument("ref_path", help="Path to the reference transcript", type=str)
    parser.add_argument("hyp_path", help="Path to the hypothesis transcript", type=str)
    args = vars(parser.parse_args())
    print(args)

    normaliser = BasicTextNormalizer() if args["non_en"] else EnglishTextNormalizer()

    ref_files, hyp_files = check_paths(args["ref_path"], args["hyp_path"])
    results = []

    for ref, hyp in zip(ref_files, hyp_files):

        norm_ref = normaliser(load_file(ref.strip()))
        norm_hyp = normaliser(load_file(hyp.strip()))

        if args["cer"] is True:
            differ, stats = run_cer(norm_ref, norm_hyp)
        else:
            differ, stats = run_wer(norm_ref, norm_hyp)

        stats["file name"] = hyp

        if args["show_normalised"] is True:
            print("NORMALISED REFERENCE:", norm_ref, sep="\n\n", end="\n\n")
            print("NORMALISED HYPOTHESIS:", norm_hyp, sep="\n\n", end="\n\n")

        if args["diff"] is True:
            differ.print_colourised_diff()

        if args["show_errors"] is True:
            differ.print_errors_by_type()

        for metric in [
            "file name",
            "wer",
            "cer",
            "reference length",
            "substitutions",
            "deletions",
            "insertions",
        ]:
            res = stats.get(metric)
            if res is not None:
                print(f"{metric}: {res}")

        results.append(stats)

    if args["csv"] is True:
        generate_csv(results, args["cer"])


if __name__ == "__main__":
    main()
