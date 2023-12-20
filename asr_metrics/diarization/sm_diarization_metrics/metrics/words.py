#!/usr/bin/env python
# encoding: utf-8

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

"""This module is original code from Speechmatics and contains
functions to produce word level diarization metrics.
"""

from .base import BaseMetric
from .matcher import HungarianMapper
from .utils import UEMSupportMixin

WDER_NAME = "word diarization error rate"

WDER_TOTAL = "number of words"
WDER_INCORRECT = "number of incorrect words"
WDER_WORD_RESULTS = "word by word results"


def get_overlap(a, b):
    """Return duration overlap beteween two passed Segments"""
    overlap = max(0, min(a.end, b.end) - max(a.start, b.start))
    return overlap


def compute_word_diarization_error_rate(reference, hypothesis_mapped, unknown_label):
    """For each hypothesis word determine if it's correct or incorrect, and return metrics"""
    nwords = 0
    incorrect = 0
    hyp_iter = hypothesis_mapped.itertracks(yield_label=True)
    ref_iter = reference.itertracks(yield_label=True)
    word_results = []
    current_ref = next(ref_iter, None)

    # Go through each word in the hypothesis
    for hyp in hyp_iter:
        nwords += 1
        word_correct = False

        # Compare to reference word(s), to find the one that has the largest overlap
        # Note: only check correctness if label is not the "unknown speaker"
        if hyp[2] != unknown_label and current_ref is not None:
            max_overlap = get_overlap(hyp[0], current_ref[0])
            max_label = current_ref[2]
            while hyp[0].end > current_ref[0].end:
                # Move on to next reference
                current_ref = next(ref_iter, None)
                if current_ref is None:
                    break
                current_overlap = get_overlap(hyp[0], current_ref[0])
                if current_overlap > max_overlap:
                    max_overlap = current_overlap
                    max_label = current_ref[2]

            # For the word with the largest overlap, do the labels match?
            if max_overlap > 0.0:
                if max_label == hyp[2]:
                    word_correct = True

        # Store results
        word_results.append((hyp[0].start, hyp[0].end, hyp[2], word_correct))
        if not word_correct:
            incorrect += 1

    return nwords, incorrect, word_results


class WordDiarizationErrorRate(UEMSupportMixin, BaseMetric):
    """Word level diarization error rate"""

    @classmethod
    def metric_name(cls):
        return WDER_NAME

    @classmethod
    def metric_components(cls):
        return [WDER_TOTAL, WDER_INCORRECT]

    def __init__(self, **kwargs):
        super(WordDiarizationErrorRate, self).__init__(**kwargs)
        self.mapper_ = HungarianMapper()
        self.unknown_label = "UU"

    def set_unknown_label(self, label):
        """Set the label used to denote Unknown speaker in the hypothesis"""
        self.unknown_label = label

    def optimal_mapping(self, reference, hypothesis, uem=None):
        """Optimal label mapping between reference and hypothesis"""
        reference, hypothesis = self.uemify(reference, hypothesis, uem=uem)
        return self.mapper_(hypothesis, reference)

    def compute_components(self, reference, hypothesis, uem=None, **kwargs):
        """Compute the mapping, and determine the word correctness rate"""

        detail = self.init_components()

        # make sure reference and hypothesis only contains string labels ('A', 'B', ...)
        reference = reference.rename_labels(generator="string")

        # make sure hypothesis only contains integer labels (1, 2, ...)
        hypothesis = hypothesis.rename_labels(generator="int")

        # optimal (int --> str) mapping
        mapping = self.optimal_mapping(reference, hypothesis, uem=uem)
        hypothesis_mapped = hypothesis.rename_labels(mapping=mapping)

        # Compute the word accuracy
        nwords, incorrect, word_results = compute_word_diarization_error_rate(
            reference, hypothesis_mapped, self.unknown_label
        )
        detail[WDER_TOTAL] = nwords
        detail[WDER_INCORRECT] = incorrect
        detail[WDER_WORD_RESULTS] = word_results

        return detail

    def compute_metric(self, detail):
        """Return metric from details"""
        numerator = detail[WDER_INCORRECT]
        denominator = detail[WDER_TOTAL]
        if denominator == 0.0:
            if numerator == 0:
                return 1.0
            else:
                raise ValueError("")
        else:
            return numerator / denominator
