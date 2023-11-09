# The MIT License (MIT)

# Copyright (c) 2021 Speechmatics

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""This module provides support functionality for dealing with different input format, etc."""

import json
import sys
from argparse import ArgumentParser
from os.path import join
from types import SimpleNamespace
from typing import Dict, List

from pyannote.core import Annotation, Segment

from .metrics.diarization import DiarizationErrorRate


def time_to_frame(time_seconds, fps=100):
    """Convert from seconds to frames"""
    return round(time_seconds * fps)


def load_dbl(filename):
    """Load the lines from a dbl file (1 entry per line)"""
    entries = []
    with open(filename) as infile:
        entries = [line.strip() for line in infile.readlines()]
    return entries


def complete_filename(basename, directory, extension):
    """Complete a filename as returned from dbl, adding directory and extension"""
    filename = basename + extension
    if directory != "":
        filename = join(directory, filename)
    return filename


def load_lab_file(filename):
    """Load label file formatted input file (<start> <end> <label>)"""
    entries = []
    with open(filename) as infile:
        for line in infile:
            line_stripped = line.strip()
            if line_stripped:
                tokens = line_stripped.split()
                if len(tokens) != 3:
                    print(f'Invalid line in lab file {filename}: "{line}"')
                    sys.exit(1)
                start_time = float(tokens[0].strip())
                end_time = float(tokens[1].strip())
                label = tokens[2].strip()
                entries.append((start_time, end_time, label))

    return entries


def load_ctm_file(filename):
    """Load CTM file formatted input file (<id> <ch> <start> <duration> <label> <score>"""
    entries = []
    with open(filename) as infile:
        for line in infile:
            line_stripped = line.strip()
            if line_stripped:
                tokens = line_stripped.split()
                if len(tokens) != 6:
                    print(f'Invalid line in ctm file {filename}: "{line}"')
                    sys.exit(1)
                start_time = float(tokens[2].strip())
                duration = float(tokens[3].strip())
                end_time = start_time + duration
                label = tokens[4].strip()
                entries.append((start_time, end_time, label))

    return entries


def load_v2_json_file(filename, get_content_type=False):
    """Load Speechmatics V2 json file, as produced by ASR transcriber.
    Returns a list of the entries (as tuples, (start, end, label).  Returns None if formatting error.
    """
    with open(filename) as fh:
        results = json.load(fh)
    if "results" in results:
        results = results["results"]

    try:
        entries = []
        for res in results:
            start_time = float(res["start_time"])
            end_time = float(res["end_time"])
            label = res["alternatives"][0].get("speaker")
            if get_content_type:
                content_type = res["type"]
                entries.append((start_time, end_time, label, content_type))
            else:
                entries.append((start_time, end_time, label))
    except KeyError:
        entries = None

    return entries


def load_reference_json_file(filename):
    """Load a standard json definition file, as used for references, etc
    This is expected to be of form:
    [
        {
            "speaker_name": "Speaker 1",
            "word": "Seems",
            "start": 0.75,
            "duration": 0.29
        },
    ]
    Returns a list of the entries (as tuples, (start, end, label).  Returns None if formatting error.
    """
    with open(filename) as fh:
        json_data = json.load(fh)
    entries = []
    try:
        for entry in json_data:
            label = entry["speaker_name"].replace(" ", "_")
            start_time = float(entry["start"])
            duration = float(entry["duration"])
            end_time = start_time + duration
            entries.append((start_time, end_time, label))
    except KeyError:
        entries = None
    return entries


def load_input_file(filename, file_type):
    """Read in the input file, returning Annotation structure for use with metric and number of frames"""
    entries = []
    nframes = 0
    file_start = -1
    file_end = 0
    if file_type == "lab":
        entries = load_lab_file(filename)
    elif file_type == "ctm":
        entries = load_ctm_file(filename)
    else:
        print(f"Invalid input type: {file_type}")
        sys.exit(1)
    data = Annotation()
    for entry in entries:
        start_frame = time_to_frame(entry[0])
        end_frame = time_to_frame(entry[1])
        speaker_label = entry[2]
        data[Segment(start_frame, end_frame)] = speaker_label
        if file_start == -1 or start_frame < file_start:
            file_start = start_frame
        file_end = max(file_end, end_frame)
    if file_start >= 0 and file_end > file_start:
        nframes = file_end - file_start
    return data, nframes


def options_from(argv: List[str]) -> Dict[str, str]:
    """Parse the input arguments, returning dictionary"""
    parser = ArgumentParser()

    parser.add_argument("dbl", type=str, help="model language")
    parser.add_argument(
        "--hyp_dir", type=str, default="", help="Hypothesis input directory"
    )
    parser.add_argument(
        "--hyp_type",
        type=str,
        default="lab",
        choices=["lab", "ctm"],
        help="Hypothesis file type",
    )
    parser.add_argument(
        "--hyp_ext",
        type=str,
        default=None,
        help="Hypothesis file extension (automatic if not set)",
    )
    parser.add_argument(
        "--ref_dir", type=str, default="", help="Reference input directory"
    )
    parser.add_argument(
        "--ref_type",
        type=str,
        default="lab",
        choices=["lab", "ctm"],
        help="Reference file type",
    )
    parser.add_argument(
        "--ref_ext",
        type=str,
        default=None,
        help="Reference file extension (automatic if not set)",
    )

    return vars(parser.parse_args(args=argv[1:]))


def main():
    args = options_from(sys.argv)
    print("Arguments: %s" % args)
    config = SimpleNamespace(**args)

    # Determine extensions
    if config.hyp_ext is not None:
        hyp_ext = config.hyp_ext
    elif config.hyp_type == "lab":
        hyp_ext = ".lab"
    else:
        hyp_ext = ".ctm"
    if config.ref_ext is not None:
        ref_ext = config.ref_ext
    elif config.ref_type == "lab":
        ref_ext = ".lab"
    else:
        ref_ext = ".ctm"

    # Load dbl file
    dbl_list = load_dbl(config.dbl)

    # Configure metric
    metric = DiarizationErrorRate()

    # Go through file by file
    print("\nFile by File Results:\n---------------------")
    total_frames = 0
    total_error_rate = 0
    total_error_rate_weighted = 0
    for filebase in dbl_list:
        filebase = filebase.strip()
        hyp_file = complete_filename(filebase, config.hyp_dir, hyp_ext)
        ref_file = complete_filename(filebase, config.ref_dir, ref_ext)
        hypothesis, nframes_hyp = load_input_file(hyp_file, config.hyp_type)
        reference, nframes_ref = load_input_file(ref_file, config.ref_type)
        nframes = max(nframes_ref, nframes_hyp)

        # Run the metrics calculations
        error_rate = metric(reference, hypothesis)

        # Build up statistics
        total_error_rate += error_rate
        total_error_rate_weighted += error_rate * nframes
        total_frames += nframes
        print(f"...{filebase} ({nframes} frames) - {error_rate * 100.0:.2f}%")

    # Give summary
    average_naive = 0.0
    if len(dbl_list) > 0:
        average_naive = (100.0 * total_error_rate) / len(dbl_list)
    average_weighted = 0.0
    if total_frames > 0:
        average_weighted = (100.0 * total_error_rate_weighted) / total_frames
    print("\nGlobal Results:\n---------------")
    print(f"Average DER (naive):    {average_naive:.2f}%")
    print(f"Average DER (weighted): {average_weighted:.2f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
