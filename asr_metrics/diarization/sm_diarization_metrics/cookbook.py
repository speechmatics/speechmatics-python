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

"""This module is original code from Speechmatics and contains useful
recipes for common tasks we need to perform when analysing diarisation.
This module features a CLI which is simpler and more approachable than the
large CLI offered by pyannote.metrics.
"""
import argparse
import json
import logging
import os
from enum import Enum
from typing import Optional

import pyannote.core

from . import utils
from .metrics import diarization as MetricsDiarization
from .metrics import segmentation as MetricsSegmentation
from .metrics import words as MetricsWords

logger = logging.getLogger(__name__)

# When converting to annotations, we combine adjacent segments if the speaker label is the same and assuming
# the gap is no larger than specified.  This value also matches that used within the diarization system at the time
# of writing, but here we wish to apply it to the reference, as also to the word level hypothesis as given via
# the v2 json output.
SEG_MERGE_GAP = 5.0
MERGE_GAP_NONE = 0.0
MERGE_GAP_ANY = -1.0

# Segment merging type, when creating annotations from file
# Depending on the file type, we may enable / disable merging.


class MergeType(Enum):
    NONE = 1
    ALL = 2
    JSON_ONLY = 3


# Tolerance (in seconds) when matching recognized speaker change point with reference
DEFAULT_SEGMENT_TOLERANCE = 1.0

# Unknown speaker label
UNKNOWN_SPEAKER = "UU"


def print_word_der_details(words):
    """Print out the word level error information"""
    print("--------------------------------")
    print("Word level diarization information:")
    for word in words:
        start_time = word[0]
        end_time = word[1]
        correct = word[3]
        if correct:
            result = "OK"
        else:
            result = "ERROR"
        print("[WDER] {:.3f} {:.3f} {}".format(start_time, end_time, result))
    print("")


def f1_score(precision, recall):
    """Compute the balance f-measure score (F1) from precision and recall"""
    if precision + recall > 0.0:
        fscore = 2.0 * (precision * recall) / (precision + recall)
    else:
        fscore = 0.0
    return fscore


def get_speaker_count_metrics(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> set:
    """Get the speaker count discrepancy metrics."""
    ref_speakers = len(set(reference.labels()) - set(["UU"]))
    hyp_speakers = len(set(hypothesis.labels()) - set(["UU"]))
    return (ref_speakers, hyp_speakers)


def get_word_level_metrics(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> set:
    """Get the error rate based on word level labelling."""
    metric = MetricsWords.WordDiarizationErrorRate()
    metric.set_unknown_label(UNKNOWN_SPEAKER)
    detailed_results = metric(reference, hypothesis, detailed=True)
    nwords = detailed_results[MetricsWords.WDER_TOTAL]
    words = detailed_results[MetricsWords.WDER_WORD_RESULTS]
    if nwords > 0:
        incorrect = detailed_results[MetricsWords.WDER_INCORRECT]
        error_rate = float(incorrect) / nwords
    else:
        error_rate = 0.0

    return (error_rate, nwords, words)


def get_der_component_details_from_annotations(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> set:
    """Given a reference and hypothesis for the diarisation of some audio as
    two `pyannote.core.Annotation` objects, returns the diarisation error rate,
    together with its component details of insertion, deletion and confusion.
    """
    metric = MetricsDiarization.DiarizationErrorRate()
    detailed_results = metric(reference, hypothesis, detailed=True)
    der = detailed_results["diarization error rate"]
    total = detailed_results["total"]
    insertion = detailed_results["false alarm"] / total
    deletion = detailed_results["missed detection"] / total
    confusion = detailed_results["confusion"] / total

    return (der, insertion, deletion, confusion)


def get_jaccard_error_rate_from_annotations(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> set:
    """Given a reference and hypothesis for the diarisation of some audio as
    two `pyannote.core.Annotation` objects, returns the Jaccard error rate.
    """
    metric = MetricsDiarization.JaccardErrorRate()
    return metric(reference, hypothesis)


def get_coverage_from_annotations(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> float:
    """Given a reference and hypothesis for the diarisation of some audio as
    two `pyannote.core.Annotation` objects, returns the diarisation coverage.
    """
    metric = MetricsDiarization.DiarizationCoverage()
    return metric(reference, hypothesis)


def get_purity_from_annotations(
    reference: pyannote.core.Annotation, hypothesis: pyannote.core.Annotation
) -> float:
    """Given a reference and hypothesis for the diarisation of some audio as
    two `pyannote.core.Annotation` objects, returns the diarisation purity.
    """
    metric = MetricsDiarization.DiarizationPurity()
    return metric(reference, hypothesis)


def get_segmentation_metrics_from_annotations(
    reference: pyannote.core.Annotation,
    hypothesis: pyannote.core.Annotation,
    tolerance: float = DEFAULT_SEGMENT_TOLERANCE,
) -> set:
    """Given a reference and hypothesis for the diarisation of some audio as
    two `pyannote.core.Annotation` objects, returns the speaker change metrics
    (recall, precision and coverage)"""
    purity = MetricsSegmentation.SegmentationPurity(tolerance=tolerance)(
        reference, hypothesis
    )
    coverage = MetricsSegmentation.SegmentationCoverage(tolerance=tolerance)(
        reference, hypothesis
    )
    precision = MetricsSegmentation.SegmentationPrecision(tolerance=tolerance)(
        reference, hypothesis
    )
    recall = MetricsSegmentation.SegmentationRecall(tolerance=tolerance)(
        reference, hypothesis
    )
    return (purity, coverage, precision, recall)


def remove_overlaps(annotation: pyannote.core.Annotation):
    """Remove any overlaps in between the segments"""
    updated_annotation = pyannote.core.Annotation()
    prev_entry = None
    for entry in annotation.itertracks(yield_label=True):
        if prev_entry is None:
            prev_entry = entry
        else:
            if prev_entry[0].end > entry[0].start:
                # We have overlap, so split at halfway point
                split_time = (prev_entry[0].end + entry[0].start) / 2.0
                updated_annotation[
                    pyannote.core.Segment(prev_entry[0].start, split_time)
                ] = prev_entry[2]
                prev_entry = (
                    pyannote.core.Segment(split_time, entry[0].end),
                    entry[1],
                    entry[2],
                )
            else:
                updated_annotation[prev_entry[0]] = prev_entry[2]
                prev_entry = entry

    if prev_entry is not None:
        updated_annotation[prev_entry[0]] = prev_entry[2]

    return updated_annotation


def merge_adjacent_segments(annotation: pyannote.core.Annotation, max_gap: float):
    """Combined adjacent segments if same speaker and if gap less than max_gap"""
    if max_gap == MERGE_GAP_NONE:
        # No merging, just return the annotation as passed in
        merged_annotation = annotation
    else:
        merged_annotation = pyannote.core.Annotation()
        prev_entry = None
        for entry in annotation.itertracks(yield_label=True):
            if prev_entry is None:
                prev_entry = entry
            else:
                if prev_entry[2] != entry[2]:
                    # A speaker label change, move on
                    merged_annotation[prev_entry[0]] = prev_entry[2]
                    prev_entry = entry
                else:
                    # Speaker label is the same
                    gap = entry[0].start - prev_entry[0].end
                    if max_gap == MERGE_GAP_ANY or gap <= max_gap:
                        # Merge. Update the previous entry with new end time.
                        update_segment = pyannote.core.Segment(
                            prev_entry[0].start, entry[0].end
                        )
                        prev_entry = (update_segment, prev_entry[1], prev_entry[2])
                    else:
                        # Do not merge. Add previous, and move on
                        merged_annotation[prev_entry[0]] = prev_entry[2]
                        prev_entry = entry

        if prev_entry is not None:
            merged_annotation[prev_entry[0]] = prev_entry[2]

    return merged_annotation


def remove_uu(annotation: pyannote.core.Annotation):
    """Remove any UU from annotation, only required for annotations produced via json"""
    return annotation.subset([UNKNOWN_SPEAKER], invert=True)


def post_process_annotation(
    annotation, max_gap_merge: float, rm_unknown: bool, rm_overlaps: bool
):
    """Merge segments in annotation, remove unknown speaker segments, etc."""
    processed_annotation = annotation
    if rm_overlaps:
        processed_annotation = remove_overlaps(processed_annotation)
    processed_annotation = merge_adjacent_segments(processed_annotation, max_gap_merge)
    if rm_unknown:
        processed_annotation = remove_uu(processed_annotation)

    return processed_annotation


def json_to_annotation(
    json_path: str,
    max_gap_merge: float = SEG_MERGE_GAP,
    rm_unknown: bool = True,
    rm_overlaps: bool = True,
) -> pyannote.core.Annotation:
    """Takes a json file specifying word level diarization results, and converts it into a `pyannote.core.Annotation`
    describing the diarisation.  Note that the input format can be either Speechmatics V2 transcription, or a
    standardized reference json format (where each entry in an unnamed list contains "speaker_name", "start", and
    "duration")
    """
    # Attempt to load in "speechmatics" transcription json format, and then back off to a
    # standardised reference format if that fails.
    entries = utils.load_v2_json_file(json_path)
    if entries is None:
        entries = utils.load_reference_json_file(json_path)
        if entries is None:
            # File does not apparently adhear to either supported format
            raise ValueError("Unsupported diarisation json format: %s", json_path)
        else:
            # Speaker UU is currently only supported with V2 json input
            rm_unknown = False

    annotation = pyannote.core.Annotation()
    for start_time, end_time, speaker_label in entries:
        annotation[pyannote.core.Segment(start_time, end_time)] = speaker_label
    final_annotation = post_process_annotation(
        annotation, max_gap_merge, rm_unknown, rm_overlaps
    )

    return final_annotation


def lab_file_to_annotation(
    lab_file_path: str,
    max_gap_merge: float = SEG_MERGE_GAP,
    rm_unknown: bool = True,
    rm_overlaps: bool = True,
) -> pyannote.core.Annotation:
    """Takes a label file (.lab) and converts it into a
    a `pyannote.core.Annotation` describing the diarisation.
    """
    entries = utils.load_lab_file(lab_file_path)
    annotation = pyannote.core.Annotation()
    for start, end, speaker_label in entries:
        annotation[pyannote.core.Segment(start, end)] = speaker_label
    final_annotation = post_process_annotation(
        annotation, max_gap_merge, rm_unknown, rm_overlaps
    )
    return final_annotation


def ctm_file_to_annotation(
    ctm_file_path: str,
    max_gap_merge: float = SEG_MERGE_GAP,
    rm_unknown: bool = True,
    rm_overlaps: bool = True,
) -> pyannote.core.Annotation:
    """Takes a .ctm file  and converts it into a `pyannote.core.Annotation`
    describing the diarisation.
    """
    entries = utils.load_ctm_file(ctm_file_path)
    annotation = pyannote.core.Annotation()
    for start, end, speaker_label in entries:
        annotation[pyannote.core.Segment(start, end)] = speaker_label
    final_annotation = post_process_annotation(
        annotation, max_gap_merge, rm_unknown, rm_overlaps
    )
    return final_annotation


def file_to_annotation(
    file_path: str,
    max_gap_merge: float = SEG_MERGE_GAP,
    rm_unknown: bool = True,
    rm_overlaps: bool = True,
):
    """Takes a file describing diarisation which can be one of several formats (.ctm, .lab, .json)
    and converts it into a `pyannote.core.Annotation` object.
    """
    file_extension = file_path.split(".")[-1]
    function_ptr = None
    if file_extension == "ctm":
        function_ptr = ctm_file_to_annotation
    elif file_extension == "lab":
        function_ptr = lab_file_to_annotation
    elif file_extension == "json":
        function_ptr = json_to_annotation
    else:
        raise ValueError(
            "Unsupported diarisation file type: %s (supported extensions: ctm, json, lab)",
            file_extension,
        )

    return function_ptr(
        file_path,
        max_gap_merge=max_gap_merge,
        rm_unknown=rm_unknown,
        rm_overlaps=rm_overlaps,
    )


def write_annotation_to_label_file(annotation, filename):
    """Write out annotation"""
    with open(filename, "w") as outfp:
        for entry in annotation.itertracks(yield_label=True):
            outfp.write("{} {} {}\n".format(entry[0].start, entry[0].end, entry[2]))


def get_der_component_details_for_files(
    reference_file: str, hypothesis_file: str
) -> set:
    """Returns the diarisation error rate and its component details for a pair of files."""
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(hypothesis_file)
    der, insertion, deletion, confusion = get_der_component_details_from_annotations(
        reference_annotation, hypothesis_annotation
    )
    return (der, insertion, deletion, confusion)


def get_unknown_speaker_count_for_files(hypothesis_file: str) -> int:
    """Get the total number of unknown speaker in the hypothesis v2 json file.
    Speaker labels of punctuations are not considered.
    If the input file is not in v2 json format, "0" will be returned."""
    hypothesis_file_extension = hypothesis_file.split(".")[-1]
    if hypothesis_file_extension == "lab" or "ctm":
        # unknown_speaker only supported for v2 json
        return 0
    entries = utils.load_v2_json_file(hypothesis_file, get_content_type=True)
    if entries is None:
        return 0
    unknown_speaker_count = 0
    for _, _, speaker_label, content_type in entries:
        if content_type == "word" and speaker_label == UNKNOWN_SPEAKER:
            unknown_speaker_count += 1
    return unknown_speaker_count


def get_coverage_for_files(reference_file: str, hypothesis_file: str) -> float:
    """Returns the diarisation coverage for a pair of files."""
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(hypothesis_file)
    diarisation_coverage = get_coverage_from_annotations(
        reference_annotation, hypothesis_annotation
    )
    return diarisation_coverage


def get_purity_for_files(reference_file: str, hypothesis_file: str) -> float:
    """Returns the diarisation purity for a pair of files."""
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(hypothesis_file)
    diarisation_purity = get_purity_from_annotations(
        reference_annotation, hypothesis_annotation
    )
    return diarisation_purity


def get_jaccard_error_rate_for_files(reference_file: str, hypothesis_file: str) -> set:
    """Returns the Jaccard error rate for a pair of files."""
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(hypothesis_file)
    return get_jaccard_error_rate_from_annotations(
        reference_annotation, hypothesis_annotation
    )


def get_segmentation_metrics_for_files(
    reference_file: str,
    hypothesis_file: str,
    tolerance: float = DEFAULT_SEGMENT_TOLERANCE,
) -> set:
    """Returns the speaker change point metrics for a pair of files."""

    # Note, we remove all gaps between segments of the same speaker, however large (thus we
    # set the max gap to MERGE_GAP_ANY).  We are only looking to analyse changes in speaker here.
    reference_annotation = file_to_annotation(
        reference_file, rm_unknown=False, max_gap_merge=MERGE_GAP_ANY
    )
    hypothesis_annotation = file_to_annotation(
        hypothesis_file, max_gap_merge=MERGE_GAP_ANY
    )
    purity, coverage, precision, recall = get_segmentation_metrics_from_annotations(
        reference_annotation, hypothesis_annotation, tolerance=tolerance
    )
    return (purity, coverage, precision, recall)


def get_speaker_count_metrics_for_files(
    reference_file: str, hypothesis_file: str
) -> tuple:
    """Returns the speaker count metrics for a pair of files"""
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(hypothesis_file)
    ref_speakers, hyp_speakers = get_speaker_count_metrics(
        reference_annotation, hypothesis_annotation
    )
    return (ref_speakers, hyp_speakers)


def get_word_level_metrics_for_files(
    reference_file: str, hypothesis_file: str
) -> tuple:
    """Returns the word level speaker labelling accuracy for a pair of files."""
    # Note, we leave UU in the hypothesis as we wish to consider words with UU, which will be considered
    # as having the wrong label.  Also, we do not perform any merging on the hypothesis, as we assume
    # these are at word level, and want to keep that so as it's over words we compute the error.
    reference_annotation = file_to_annotation(reference_file, rm_unknown=False)
    hypothesis_annotation = file_to_annotation(
        hypothesis_file, max_gap_merge=MERGE_GAP_NONE, rm_unknown=False
    )
    error_rate, nwords, words = get_word_level_metrics(
        reference_annotation, hypothesis_annotation
    )
    unknown_speaker = get_unknown_speaker_count_for_files(hypothesis_file)
    speaker_uu_percentage = unknown_speaker / nwords
    return (error_rate, nwords, words, speaker_uu_percentage)


def get_diarisation_file_duration_seconds(file_path: str) -> float:
    """Returns the duration of the file based on the end of the last labelled segment"""
    annotation = file_to_annotation(file_path)
    max_time = -1
    for entry in annotation.itertracks(yield_label=True):
        max_time = max(max_time, entry[0].end)
    return max_time


def get_diarisation_labelled_duration_seconds(file_path: str) -> float:
    """Returns the duration of labelled data (not including UU) in the file."""
    annotation = file_to_annotation(file_path, rm_unknown=True)
    return annotation.get_timeline(copy=False).duration()


def get_data_set_results(
    reference_dbl: str,
    hypothesis_dbl: str,
    dbl_root: Optional[str] = os.getcwd(),
    seg_tolerance=DEFAULT_SEGMENT_TOLERANCE,
    allow_none_hyp_lab: bool = False,
) -> dict:
    """Takes as input two DBL files describing the list of corresponding reference
    and hypothesis files. Returns a dictionary containing results for different
    diarisation metrics"""
    overall_results = {}
    file_results = []
    references = utils.load_dbl(reference_dbl)
    hypotheses = utils.load_dbl(hypothesis_dbl)

    weighted_diarisation_error_rates = []
    weighted_der_insertion = []
    weighted_der_deletion = []
    weighted_der_confusion = []
    weighted_jaccard_error_rates = []
    weighted_diarisation_purities = []
    weighted_diarisation_coverage = []
    weighted_segmentation_coverage = []
    weighted_segmentation_purity = []
    weighted_segmentation_precision = []
    weighted_segmentation_recall = []
    weighted_segmentation_f1 = []
    weighted_word_der = []
    speaker_uu_percentages = []
    total_audio_duration = 0
    total_ref_duration = 0
    total_hyp_duration = 0
    total_nwords = 0
    total_nfiles = len(references)
    total_ref_speakers = 0
    total_hyp_speakers = 0
    total_files_nspeakers_correct = 0
    total_files_nspeakers_plus_one = 0
    total_files_nspeakers_plus_many = 0
    total_files_nspeakers_minus_one = 0
    total_files_nspeakers_minus_many = 0
    total_files_single_speaker_issue = 0
    total_speaker_discrepancy = 0

    for i, (ref, hyp) in enumerate(zip(references, hypotheses)):
        logger.debug(
            "Computing results for files: ref=%s, hyp=%s. Progress: %d/%d",
            ref,
            hyp,
            i + 1,
            len(references),
        )

        if dbl_root is not None:
            ref_path = os.path.join(dbl_root, ref)
            hyp_path = os.path.join(dbl_root, hyp)
        else:
            ref_path = ref
            hyp_path = hyp

        # Reference duration, used to weight results
        audio_duration = get_diarisation_file_duration_seconds(ref_path)
        ref_duration = get_diarisation_labelled_duration_seconds(ref_path)
        hyp_duration = get_diarisation_labelled_duration_seconds(hyp_path)
        total_audio_duration += audio_duration
        total_ref_duration += ref_duration
        total_hyp_duration += hyp_duration

        if not os.path.isfile(
            hyp_path
        ):  # current VAD doesn't give output for some telephony data in RT mode
            if hyp_path.endswith(".lab"):
                if allow_none_hyp_lab:
                    with open(hyp_path, "w") as fake_hyp:
                        fake_hyp.write(
                            f"0.000 {str(audio_duration)} {UNKNOWN_SPEAKER}\n"
                        )
                else:
                    raise ValueError(
                        f"Hypothesis lab does not exist: {hyp_path}, use --allow-none-hyp-lab for creating dummy lab"
                    )
            elif hyp_path.endswith(".json"):
                raise ValueError(f"Hypothesis json does not exist: {hyp_path}")

        # DER and related metrics
        der, insertion, deletion, confusion = get_der_component_details_for_files(
            ref_path, hyp_path
        )
        weighted_diarisation_error_rates.append(der * ref_duration)
        weighted_der_insertion.append(insertion * ref_duration)
        weighted_der_deletion.append(deletion * ref_duration)
        weighted_der_confusion.append(confusion * ref_duration)

        # Further speaker diarization metrics
        diarisation_purity = get_purity_for_files(ref_path, hyp_path)
        diarisation_coverage = get_coverage_for_files(ref_path, hyp_path)
        weighted_diarisation_purities.append(diarisation_purity * ref_duration)
        weighted_diarisation_coverage.append(diarisation_coverage * ref_duration)

        # Jaccard error rate and related metrics
        jaccard_error_rate = get_jaccard_error_rate_for_files(ref_path, hyp_path)
        weighted_jaccard_error_rates.append(jaccard_error_rate * ref_duration)

        # Speaker change metrics
        (
            seg_purity,
            seg_coverage,
            seg_precision,
            seg_recall,
        ) = get_segmentation_metrics_for_files(
            ref_path, hyp_path, tolerance=seg_tolerance
        )
        seg_f1_score = f1_score(seg_precision, seg_recall)
        weighted_segmentation_purity.append(seg_purity * ref_duration)
        weighted_segmentation_coverage.append(seg_coverage * ref_duration)
        weighted_segmentation_precision.append(seg_precision * ref_duration)
        weighted_segmentation_recall.append(seg_recall * ref_duration)
        weighted_segmentation_f1.append(seg_f1_score * ref_duration)

        # Word level DER
        word_der, nwords, _, speaker_uu_percentage = get_word_level_metrics_for_files(
            ref_path, hyp_path
        )
        weighted_word_der.append(word_der * nwords)
        speaker_uu_percentages.append(speaker_uu_percentage)
        total_nwords += nwords

        # Speaker counts
        ref_speakers, hyp_speakers = get_speaker_count_metrics_for_files(
            ref_path, hyp_path
        )
        total_ref_speakers += ref_speakers
        total_hyp_speakers += hyp_speakers
        total_speaker_discrepancy += abs(ref_speakers - hyp_speakers)
        rate_nspeakers_correct = 0.0
        rate_nspeakers_plus_one = 0.0
        rate_nspeakers_plus_many = 0.0
        rate_nspeakers_minus_one = 0.0
        rate_nspeakers_minus_many = 0.0
        rate_single_speaker_issue = 0.0
        if ref_speakers == hyp_speakers:
            total_files_nspeakers_correct += 1
            rate_nspeakers_correct = 1.0
        elif hyp_speakers > ref_speakers:
            if (hyp_speakers - ref_speakers) == 1:
                total_files_nspeakers_plus_one += 1
                rate_nspeakers_plus_one = 1.0
            else:
                total_files_nspeakers_plus_many += 1
                rate_nspeakers_plus_many = 1.0
        else:
            if hyp_speakers == 1:
                total_files_single_speaker_issue += 1
                rate_single_speaker_issue = 1.0
            if (ref_speakers - hyp_speakers) == 1:
                total_files_nspeakers_minus_one += 1
                rate_nspeakers_minus_one = 1.0
            else:
                total_files_nspeakers_minus_many += 1
                rate_nspeakers_minus_many = 1.0

        nspeakers_discrepancy = hyp_speakers - ref_speakers

        # Store the results for this particular file
        file_result = {}
        file_result["reference"] = ref_path
        file_result["hypothesis"] = hyp_path
        file_result["audio_duration"] = audio_duration
        file_result["ref_duration"] = ref_duration
        file_result["hyp_duration"] = hyp_duration
        file_result["audio_labelled"] = hyp_duration / audio_duration
        file_result["ref_labelled"] = hyp_duration / ref_duration
        file_result["der"] = der
        file_result["insertion"] = insertion
        file_result["deletion"] = deletion
        file_result["conf"] = confusion
        file_result["purity"] = diarisation_purity
        file_result["coverage"] = diarisation_coverage
        file_result["jer"] = jaccard_error_rate
        file_result["seg_purity"] = seg_purity
        file_result["seg_coverage"] = seg_coverage
        file_result["seg_precision"] = seg_precision
        file_result["seg_recall"] = seg_recall
        file_result["seg_f1_score"] = seg_f1_score
        file_result["word_der"] = word_der
        file_result["speaker_uu_percentage"] = speaker_uu_percentage
        file_result["ref_speakers"] = ref_speakers
        file_result["hyp_speakers"] = hyp_speakers
        file_result["nspeakers_discrepancy"] = nspeakers_discrepancy
        file_result["abs_nspeakers_discrepancy"] = abs(nspeakers_discrepancy)
        file_result["rate_nspeakers_correct"] = rate_nspeakers_correct
        file_result["rate_nspeakers_plus_one"] = rate_nspeakers_plus_one
        file_result["rate_nspeakers_plus_many"] = rate_nspeakers_plus_many
        file_result["rate_nspeakers_minus_one"] = rate_nspeakers_minus_one
        file_result["rate_nspeakers_minus_many"] = rate_nspeakers_minus_many
        file_result["rate_single_speaker_issue"] = rate_single_speaker_issue
        file_results.append(file_result)

    # Compute averages across set
    if total_nwords > 0:
        average_word_der = sum(weighted_word_der) / total_nwords
        average_speaker_uu_percentage = sum(speaker_uu_percentages) / len(
            speaker_uu_percentages
        )
    else:
        average_word_der = 0.0
        average_speaker_uu_percentage = 0

    overall_results["total_audio_duration"] = total_audio_duration
    overall_results["total_ref_duration"] = total_ref_duration
    overall_results["total_hyp_duration"] = total_hyp_duration
    overall_results["audio_labelled"] = total_hyp_duration / total_audio_duration
    overall_results["ref_labelled"] = total_hyp_duration / total_ref_duration
    overall_results["total_nwords"] = total_nwords

    overall_results["average_der"] = (
        sum(weighted_diarisation_error_rates) / total_ref_duration
    )
    overall_results["average_jer"] = (
        sum(weighted_jaccard_error_rates) / total_ref_duration
    )
    overall_results["average_insertion"] = (
        sum(weighted_der_insertion) / total_ref_duration
    )
    overall_results["average_deletion"] = (
        sum(weighted_der_deletion) / total_ref_duration
    )
    overall_results["average_confusion"] = (
        sum(weighted_der_confusion) / total_ref_duration
    )

    overall_results["average_diarisation_coverage"] = (
        sum(weighted_diarisation_coverage) / total_ref_duration
    )
    overall_results["average_diarisation_purity"] = (
        sum(weighted_diarisation_purities) / total_ref_duration
    )

    overall_results["average_segmentation_coverage"] = (
        sum(weighted_segmentation_coverage) / total_ref_duration
    )
    overall_results["average_segmentation_purity"] = (
        sum(weighted_segmentation_purity) / total_ref_duration
    )
    overall_results["average_segmentation_precision"] = (
        sum(weighted_segmentation_precision) / total_ref_duration
    )
    overall_results["average_segmentation_recall"] = (
        sum(weighted_segmentation_recall) / total_ref_duration
    )
    overall_results["average_segmentation_f1"] = (
        sum(weighted_segmentation_f1) / total_ref_duration
    )

    overall_results["average_word_der"] = average_word_der
    overall_results["average_speaker_uu_percentage"] = average_speaker_uu_percentage

    # Speaker count statistics
    if total_nfiles > 0:
        avg_nspeakers_ref = total_ref_speakers / total_nfiles
        avg_nspeakers_hyp = total_hyp_speakers / total_nfiles
        nspeakers_correct_rate = total_files_nspeakers_correct / total_nfiles
        nspeakers_plus_one_rate = total_files_nspeakers_plus_one / total_nfiles
        nspeakers_plus_many_rate = total_files_nspeakers_plus_many / total_nfiles
        nspeakers_minus_one_rate = total_files_nspeakers_minus_one / total_nfiles
        nspeakers_minus_many_rate = total_files_nspeakers_minus_many / total_nfiles
        single_speaker_issue_rate = total_files_single_speaker_issue / total_nfiles
        overall_results["average_nspeakers_ref"] = avg_nspeakers_ref
        overall_results["average_nspeakers_hyp"] = avg_nspeakers_hyp
        overall_results["average_nspeakers_discrepancy"] = (
            avg_nspeakers_hyp - avg_nspeakers_ref
        )
        overall_results["average_nspeakers_abs_discrepancy"] = (
            total_speaker_discrepancy / total_nfiles
        )
        overall_results["rate_nspeakers_correct"] = nspeakers_correct_rate
        overall_results["rate_nspeakers_plus_one"] = nspeakers_plus_one_rate
        overall_results["rate_nspeakers_plus_many"] = nspeakers_plus_many_rate
        overall_results["rate_nspeakers_minus_one"] = nspeakers_minus_one_rate
        overall_results["rate_nspeakers_minus_many"] = nspeakers_minus_many_rate
        overall_results["rate_single_speaker_issue"] = single_speaker_issue_rate
    else:
        overall_results["average_nspeakers_ref"] = 0.0
        overall_results["average_nspeakers_hyp"] = 0.0
        overall_results["average_nspeakers_discrepancy"] = 0.0
        overall_results["average_nspeakers_abs_discrepancy"] = 0.0
        overall_results["rate_nspeakers_correct"] = 0.0
        overall_results["rate_nspeakers_plus_one"] = 0.0
        overall_results["rate_nspeakers_plus_many"] = 0.0
        overall_results["rate_nspeakers_minus_one"] = 0.0
        overall_results["rate_nspeakers_minus_many"] = 0.0
        overall_results["rate_single_speaker_issue"] = 0.0

    return overall_results, file_results


def output_results_as_json(
    parameters: dict, overall_results: dict, file_results: list, outdir: str
):
    """Takes in the results data and output as a json file"""
    final_json_output = {}
    final_json_output["args"] = parameters
    final_json_output["files"] = file_results
    final_json_output["overall"] = overall_results
    json_output_path = os.path.join(outdir, "results.json")
    with open(json_output_path, "w") as result_json_file:
        json.dump(final_json_output, result_json_file)


def output_results_as_csv(
    overall_results: dict, file_results: list, overall_csv: str, details_csv: str
):
    """Takes in the results data and output as a csv file"""

    # Write the results for each file (including header)
    if len(file_results) == 0:
        raise RuntimeError("No file results found, so aborting CSV output")
    header = (
        str(list(file_results[0].keys()))
        .replace("]", "")
        .replace("[", "")
        .replace("'", "")
    )
    with open(details_csv, "w") as cfh:
        print(header, file=cfh)
        for file_result in file_results:
            values = (
                str(list(file_result.values()))
                .replace("]", "")
                .replace("[", "")
                .replace("'", "")
            )
            print(values, file=cfh)

    # Now write the overall results
    header = (
        str(list(overall_results.keys()))
        .replace("]", "")
        .replace("[", "")
        .replace("'", "")
    )
    with open(overall_csv, "w") as cfh:
        print(header, file=cfh)
        values = (
            str(list(overall_results.values()))
            .replace("]", "")
            .replace("[", "")
            .replace("'", "")
        )
        print(values, file=cfh)


def get_diarization_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "reference_file",
        type=str,
        help=(
            "A file describing the true diarisation of some audio."
            " Several formats are supported including 'dbl', 'ctm', 'lab' and"
            " Speechmatics V2 'json'"
        ),
    )
    parser.add_argument(
        "hypothesis_file",
        type=str,
        help=(
            "A file describing the hypothesised diarisation of some audio."
            " Several formats are supported including 'dbl', 'ctm', 'lab' and"
            " Speechmatics V2 'json'"
        ),
    )
    parser.add_argument(
        "--dbl-root",
        type=str,
        default=os.getcwd(),
        help=(
            "If using DBL input then this argument specifies the root directory "
            "for files listed in the DBL."
        ),
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="json",
        help=(
            "Output mertics scores for data set and each file in a certain format"
            "can choose between json or csv"
        ),
    )
    parser.add_argument(
        "--segmentation-tolerance",
        type=float,
        default=DEFAULT_SEGMENT_TOLERANCE,
        help=(
            "Tolerance in seconds when matching hypothesised change point gwith that in the reference (in seconds)"
        ),
    )
    parser.add_argument(
        "--show-words",
        action="store_true",
        default=False,
        help=(
            "Show the words (if using json hypothesis) alongside whether correct or not."
        ),
    )
    parser.add_argument(
        "--output-hyp-label",
        type=str,
        default=None,
        help=("Output hypothesis label file (for single file pair only, not DBL)."),
    )
    parser.add_argument(
        "--allow-none-hyp-lab",
        type=str,
        default=False,
        help=(
            "If missing, create a dummy hypothesis lab file with all speakers set to 'UU'"
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=("Enable debugging information."),
    )

    parser.add_argument(
        "--outdir", type=str, default=None, help=("Output directory (OPTIONAL).")
    )
    return parser


def main(args: Optional[argparse.Namespace] = None):
    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "reference_file",
    #     type=str,
    #     help=(
    #         "A file describing the true diarisation of some audio."
    #         " Several formats are supported including 'dbl', 'ctm', 'lab' and"
    #         " Speechmatics V2 'json'"
    #     ),
    # )
    # parser.add_argument(
    #     "hypothesis_file",
    #     type=str,
    #     help=(
    #         "A file describing the hypothesised diarisation of some audio."
    #         " Several formats are supported including 'dbl', 'ctm', 'lab' and"
    #         " Speechmatics V2 'json'"
    #     ),
    # )
    # parser.add_argument(
    #     "--dbl-root",
    #     type=str,
    #     default=os.getcwd(),
    #     help=(
    #         "If using DBL input then this argument specifies the root directory "
    #         "for files listed in the DBL."
    #     ),
    # )
    # parser.add_argument(
    #     "--output-format",
    #     type=str,
    #     default="json",
    #     help=(
    #         "Output mertics scores for data set and each file in a certain format"
    #         "can choose between json or csv"
    #     ),
    # )
    # parser.add_argument(
    #     "--segmentation-tolerance",
    #     type=float,
    #     default=DEFAULT_SEGMENT_TOLERANCE,
    #     help=(
    #         "Tolerance in seconds when matching hypothesised change point gwith that in the reference (in seconds)"
    #     ),
    # )
    # parser.add_argument(
    #     "--show-words",
    #     action="store_true",
    #     default=False,
    #     help=(
    #         "Show the words (if using json hypothesis) alongside whether correct or not."
    #     ),
    # )
    # parser.add_argument(
    #     "--output-hyp-label",
    #     type=str,
    #     default=None,
    #     help=("Output hypothesis label file (for single file pair only, not DBL)."),
    # )
    # parser.add_argument(
    #     "--allow-none-hyp-lab",
    #     type=str,
    #     default=False,
    #     help=(
    #         "If missing, create a dummy hypothesis lab file with all speakers set to 'UU'"
    #     ),
    # )
    # parser.add_argument(
    #     "--debug",
    #     action="store_true",
    #     help=("Enable debugging information."),
    # )

    # parser.add_argument(
    #     "--outdir", type=str, default=None, help=("Output directory (OPTIONAL).")
    # )
    # args = parser.parse_args()
    if args is None:
        parser = get_diarization_args(argparse.ArgumentParser())
        args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(message)s",
        handlers=[logging.StreamHandler()],
    )

    assert os.path.isfile(args.reference_file)
    assert os.path.isfile(args.hypothesis_file)

    if args.outdir is not None:
        outdir = args.outdir
    else:
        outdir = "/".join(args.hypothesis_file.split("/")[:-1])

    reference_file_extension = args.reference_file.split(".")[-1]
    hypothesis_file_extension = args.reference_file.split(".")[-1]

    if "dbl" in [reference_file_extension, hypothesis_file_extension]:
        # Process over a set of files (pairs of hypothesis / reference)
        if not (
            reference_file_extension == "dbl" and hypothesis_file_extension == "dbl"
        ):
            raise ValueError("If using DBL input then both files must be DBLs")

        overall_results, file_results = get_data_set_results(
            args.reference_file,
            args.hypothesis_file,
            dbl_root=args.dbl_root,
            seg_tolerance=args.segmentation_tolerance,
            allow_none_hyp_lab=args.allow_none_hyp_lab,
        )

        if args.output_format == "json":
            parameters = {}
            parameters["reference_file"] = args.reference_file
            parameters["hypothesis_file"] = args.hypothesis_file
            parameters["--dbl-root"] = args.dbl_root
            output_results_as_json(parameters, overall_results, file_results, outdir)

        if args.output_format == "csv":
            details_csv = os.path.join(outdir, "results-details.csv")
            overall_csv = os.path.join(outdir, "results-summary.csv")
            output_results_as_csv(
                overall_results, file_results, overall_csv, details_csv
            )
    else:
        # Compute metrics on a single hypothesis / reference pair
        audio_duration = get_diarisation_file_duration_seconds(args.reference_file)
        ref_duration = get_diarisation_labelled_duration_seconds(args.reference_file)
        hyp_duration = get_diarisation_labelled_duration_seconds(args.hypothesis_file)
        audio_labelled = hyp_duration / audio_duration
        ref_labelled = hyp_duration / ref_duration

        der, insertion, deletion, confusion = get_der_component_details_for_files(
            args.reference_file, args.hypothesis_file
        )
        diarization_coverage = get_coverage_for_files(
            args.reference_file, args.hypothesis_file
        )
        diarization_purity = get_purity_for_files(
            args.reference_file, args.hypothesis_file
        )
        jaccard_error_rate = get_jaccard_error_rate_for_files(
            args.reference_file, args.hypothesis_file
        )
        (
            segment_purity,
            segment_coverage,
            segment_precision,
            segment_recall,
        ) = get_segmentation_metrics_for_files(
            args.reference_file,
            args.hypothesis_file,
            tolerance=args.segmentation_tolerance,
        )
        segment_F1_score = f1_score(segment_precision, segment_recall)
        (
            word_der,
            nwords,
            words,
            speaker_uu_percentage,
        ) = get_word_level_metrics_for_files(args.reference_file, args.hypothesis_file)
        nspeakers_reference, nspeakers_hypothesis = get_speaker_count_metrics_for_files(
            args.reference_file, args.hypothesis_file
        )

        # Output hypothesis as label if required
        if args.output_hyp_label is not None:
            annotation = file_to_annotation(args.hypothesis_file)
            write_annotation_to_label_file(annotation, args.output_hyp_label)
            print("Wrote hypothesis label file: {}".format(args.output_hyp_label))

        # Show the word level error information if required
        if args.show_words:
            print_word_der_details(words)

        # Show the summary of metrics (for single file)
        print("--------------------------------")
        print("Audio Duration (s):         {:.3f}s".format(audio_duration))
        print("Reference Labelled (s)      {:.3f}s".format(ref_duration))
        print("Hypothesis Labelled (s)     {:.3f}s".format(hyp_duration))
        print("Audio labelled:             {:.3f}".format(audio_labelled))
        print("Ref labelled:               {:.3f}".format(ref_labelled))
        print("--------------------------------")
        print("DER:                        {:.3f}".format(der))
        print("Insertion:                  {:.3f}".format(insertion))
        print("Deletion:                   {:.3f}".format(deletion))
        print("Confusion:                  {:.3f}".format(confusion))
        print("--------------------------------")
        print("Diarization Coverage:       {:.3f}".format(diarization_coverage))
        print("Diarization Purity:         {:.3f}".format(diarization_purity))
        print("--------------------------------")
        print("Jaccard Error Rate:         {:.3f}".format(jaccard_error_rate))
        print("--------------------------------")
        print("Segmentation Coverage:      {:.3f}".format(segment_purity))
        print("Segmentation Purity:        {:.3f}".format(segment_coverage))
        print("Segmentation Precision:     {:.3f}".format(segment_precision))
        print("Segmentation Recall:        {:.3f}".format(segment_recall))
        print("Segmentation F1 Score:      {:.3f}".format(segment_F1_score))
        print("--------------------------------")
        print("Word level DER:             {:.3f}".format(word_der))
        print("Speaker UU percentage:      {:.3f}".format(speaker_uu_percentage))
        print("--------------------------------")
        print("NSpeakers Reference:        {}".format(nspeakers_reference))
        print("NSpeakers Hypothesis:       {}".format(nspeakers_hypothesis))
        print(
            "NSpeakers Discrepancy:      {}".format(
                nspeakers_hypothesis - nspeakers_reference
            )
        )
        print("--------------------------------")


if __name__ == "__main__":
    main()
