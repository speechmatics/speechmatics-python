# Speechmatics WER Benchmarking

WER is a metric commonly used for benchmarking Automatic Speech Recognition accuracy.

It compares a perfect Reference transcript against the ASR transcript, also known as the Hypothesis transcript. The metric itself measures the minimum number of edits required to correct the Hypothesis transcript into the perfect Reference transcript. The number of edits is normalised by the number of words in the Reference transcript, meaning that the WER can be compared across files with different number of words in.

## Normalisation

The Reference and Hypothesis transcripts are often normalised, so as not to penalise mistakes due to differences in capitalisation, punctuation or formatting. This can involve some of the following steps:

1. Converting all letters to lowercase
2. Converting symbols to their written form (currencies, numbers and ordinals for instance)
3. Converting all whitespace to single spaces
4. Converting contractions to their written form (e.g., Dr. -> doctor)
5. Converting alternative spellings to a common form (e.g., colourise -> colorize)
6. Removing punctuation

This is not an exhaustive list, and there will often be edge cases which need to be investigated.

## Types of Errors

Errors (or edits to the hypothesis) are categorised into Insertions, Deletions and Substitutions.

- Insertions means the Hypothesis transcript contains words not in the original audio
- Deletions means the Hypothesis transcript didn't transcribe words that did appear in the original audio
- Substitutions means the Hypothesis transcript exchanged one word for another, compared with the original audio

Adding up all the occurences of each type of error gives us the total number of errors, known as the Minimum Edit Distance or Levenshtein Distance. Dividing by the total number of words in the Reference, N, gives us the WER as follows:

$$ \text{WER} = \frac{I + D + S}{N}$$

Accuracy is the complement of WER. That is, if the WER of an ASR transcript if 5 %, it's Accuracy would be 95 %, since 5 % + 95 % = 100 %

## Usage

This WER tool is built using the JiWER library. Install it as follows:

```bash
pip3 install jiwer regex
```

To compute the WER and show a transcript highlighting the difference between the Reference and the Hypothesis, run the following:

```bash
python3 -m metrics.wer --diff <reference_path> <hypothesis_path>
```

## Read More

- [The Future of Word Error Rate](https://www.speechmatics.com/company/articles-and-news/the-future-of-word-error-rate?utm_source=facebook&utm_medium=social&fbclid=IwAR1z7ZU4WowgDBs91MNKFTwPACD9gb7dkrQpkr1HmfsgXPv-Ndt5PeySjIk&restored=1676632411598)
- [Speech and Language Processing, Ch 2.](https://web.stanford.edu/~jurafsky/slp3/2.pdf) by Jurafsky and Martin
