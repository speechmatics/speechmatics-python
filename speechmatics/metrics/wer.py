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
from speechmatics.metrics.normalizers import BasicTextNormalizer, EnglishTextNormalizer


class DiffColours:
    """
    Class to define the colours used in a diff
    See here: https://tforgione.fr/posts/ansi-escape-codes/
    """

    green = "\x1b[38;5;16;48;5;2m"
    red = "\x1b[38;5;16;48;5;1m"
    yellow = "\x1b[0;30;43m"
    endcolour = "\x1b[0m"


def load_file(path) -> str:
    """
    Returns a string containing the contents of a file, given the file path
    """
    with open(path, "r", encoding="utf-8") as input_path:
        return input_path.read()


def read_dbl(path) -> list[str]:
    """
    Returns a list of file path, given an input DBL file path
    """
    with open(path, "r", encoding="utf-8") as input_path:
        return input_path.readlines()


def diff_strings(
    ref: list, hyp: list, join_token: str = " "
) -> Tuple[list, list, list, list]:
    """
    Show a colourised diff between two input strings.

    Args:
        ref (list): a list of tokens from the reference transcript.
        hyp (list): a list of tokens from the hypothesis transcript.
        join_token (str): the character between input tokens. Defaults to a single space.

    Returns:
        A 4-tuple with the following:

        output (list): list of colourised transcript segments  using ANSI Escape codes
        insertions (list): list of inserted segments in the hypothesis transcript
        deletions (list): list of deleted segments from the reference transcript
        substitutions (list): list of substituted segments from the reference to the hypothesis

    """
    output = []
    insertions = []
    deletions = []
    substitutions = []
    matcher = difflib.SequenceMatcher(None, ref, hyp)

    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():

        if opcode == "equal":
            output.append(join_token.join(ref[a0:a1]))

        if opcode == "insert":
            segment = join_token.join(hyp[b0:b1])
            output.append(f"{DiffColours.green}{segment}{DiffColours.endcolour}")
            insertions.append(segment)

        if opcode == "delete":
            segment = join_token.join(ref[a0:a1])
            output.append(f"{DiffColours.red}{segment}{DiffColours.endcolour}")
            deletions.append(segment)

        if opcode == "replace":
            ref_segment = join_token.join(ref[a0:a1])
            hyp_segment = join_token.join(hyp[b0:b1])
            output.append(
                f"{DiffColours.yellow}{ref_segment} -> {hyp_segment}{DiffColours.endcolour}"
            )
            substitutions.append(f"{ref_segment} -> {hyp_segment}")

    return output, insertions, deletions, substitutions


def count_errors(errors_list: list) -> list[tuple[Any, int]]:
    """
    Use Counter.most_common() to list errors by the number of times they occur

    Args:
        errors_list (list): a list of errors to be enumerated

    Returns:
        list of tuples in the form (error, number of occurances)
    """
    return Counter(errors_list).most_common()


def print_colourised_diff(diff: str) -> None:
    """
    Prints the colourised diff and error key

    Arguments:
        diff (str): the colourised diff as a single string
    """
    print("DIFF", end="\n\n")
    print(f"{DiffColours.green}INSERTION{DiffColours.endcolour}")
    print(f"{DiffColours.red}DELETION{DiffColours.endcolour}")
    print(f"{DiffColours.yellow}SUBSTITUTION{DiffColours.endcolour}", end="\n\n")
    print(diff, end="\n\n")


def print_errors_chronologically(
    insertions: list, deletions: list, replacements: list
) -> None:
    """
    Print the errors as they appear in the transcript.

    Args:
        insertions (list): list of inserted segments in the hypothesis transcript
        deletions (list): list of deleted segments from the reference transcript
        substitutions (list): list of substituted segments from the reference to the hypothesis
    """
    if len(insertions) > 0:
        print(f"{DiffColours.green}INSERTIONS:{DiffColours.endcolour}")
        for example in insertions:
            print(f"'{example}'", end="\n")

    if len(deletions) > 0:
        print(f"{DiffColours.red}DELETIONS:{DiffColours.endcolour}")
        for example in deletions:
            print(f"'{example}'", end="\n")

    if len(replacements) > 0:
        print(
            f"{DiffColours.yellow}SUBSTITUTIONS: (REFERENCE -> HYPOTHESIS):{DiffColours.endcolour}",
            end="\n",
        )
        for example in replacements:
            print(f"'{example}'", end="\n")

    print("\n\n")


def print_errors_by_prevelance(
    insertions: list, deletions: list, replacements: list
) -> None:
    """
    Print the errors and the number of times they occur, in order of most -> least

    Args:
        insertions (list): list of inserted segments in the hypothesis transcript
        deletions (list): list of deleted segments from the reference transcript
        substitutions (list): list of substituted segments from the reference to the hypothesis
    """
    print(f"{DiffColours.green}INSERTIONS:{DiffColours.endcolour}")
    for error, count in count_errors(insertions):
        print(f"'{error}':   {count}")

    print(f"{DiffColours.red}DELETIONS:{DiffColours.endcolour}")
    for error, count in count_errors(deletions):
        print(f"'{error}':   {count}")

    print(
        f"{DiffColours.yellow}SUBSTITUTIONS: (REFERENCE -> HYPOTHESIS):{DiffColours.endcolour}"
    )
    for error, count in count_errors(replacements):
        print(f"'{error}':   {count}")

    print("\n\n")


def is_supported(file_name: str) -> bool:
    "Takes input file name, checks if file is valid"
    return file_name.endswith((".dbl", ".txt"))


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
        "--common-errors", help="Show common misrecognitions", action="store_true"
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

    if (
        is_supported(args["ref_path"]) is not True
        or is_supported(args["hyp_path"]) is not True
    ):
        raise ValueError("Unsupported file type, files must be .dbl or .txt files")

    if args["ref_path"].endswith(".dbl") and args["ref_path"].endswith(".dbl"):
        ref_files = read_dbl(args["ref_path"])
        hyp_files = read_dbl(args["hyp_path"])
        assert len(ref_files) == len(
            hyp_files
        ), "Number of ref and hyp files should be the same"

    if args["ref_path"].endswith(".txt") and args["ref_path"].endswith(".txt"):
        ref_files = [args["ref_path"]]
        hyp_files = [args["hyp_path"]]

    results = []

    for ref, hyp in zip(ref_files, hyp_files):

        raw_ref = load_file(ref.strip())
        raw_hyp = load_file(hyp.strip())
        norm_ref = normaliser(raw_ref)
        norm_hyp = normaliser(raw_hyp)

        if args["cer"] is True:
            stats = cer(norm_ref, norm_hyp, return_dict=True)
            stats["reference length"] = len(list(norm_ref))
            stats["accuracy"] = 1 - stats["cer"]
            diff, insertions, deletions, replacements = diff_strings(
                list(norm_ref), list(norm_hyp), join_token=""
            )

        else:
            stats = compute_measures(norm_ref, norm_hyp)
            stats["reference length"] = len(norm_ref.split())
            stats["accuracy"] = 1 - stats["wer"]
            diff, insertions, deletions, replacements = diff_strings(
                norm_ref.split(), norm_hyp.split(), join_token=" "
            )

        stats["file name"] = hyp

        if args["show_normalised"] is True:
            print("NORMALISED REFERENCE:", norm_ref, sep="\n\n", end="\n\n")
            print("NORMALISED HYPOTHESIS:", norm_hyp, sep="\n\n", end="\n\n")

        if args["diff"] is True:
            diff = "".join(diff) if args["cer"] is True else " ".join(diff)
            print_colourised_diff(diff)

        if args["common_errors"] is True:
            print_errors_by_prevelance(insertions, deletions, replacements)

        if args["common_errors"] is not True and args["diff"] is True:
            print_errors_chronologically(insertions, deletions, replacements)

        for metric, val in stats.items():
            print(f"{metric}: {val}")

        results.append(stats)

    if args["csv"] is True:

        if args["cer"] is True:
            fields = [
                "file name",
                "cer",
                "accuracy",
                "insertions",
                "deletions",
                "substitutions",
                "reference length",
            ]

        else:
            fields = [
                "file name",
                "wer",
                "accuracy",
                "insertions",
                "deletions",
                "substitutions",
                "reference length",
            ]

        with open("results.csv", "w", encoding="utf-8") as results_csv:
            writer = csv.DictWriter(
                results_csv, fieldnames=fields, extrasaction="ignore"
            )
            writer.writeheader()
            for row in results:
                writer.writerow(row)


if __name__ == "__main__":
    main()
