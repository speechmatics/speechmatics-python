# Diarisation metrics we use

In cookbook.py, there're the implementations of three metrics used to evaluate diarisation performance. They are diarisation error rate (DER),
diarisation purity (DP), and diarisation coverage (DC).

## Diarisation error rate (DER)

Diarisation error rate (DER) is the standard metric for evaluating and comparing speaker diarisation systems. It is defined as follows:
### DER = ( false alarm + missed detection + confusion ) / total
Where false alarm is the duration of non-speech incorrectly classified as speech, missed detection is the duration of speech incorrectly classified as non-speech, confusion is the duration of speaker confusion, and total is the total duration of speech in the reference.

## Diarisation purity (DP) and diarisation coverage (DC)

While the diarisation error rate provides a convenient way to compare different diarisation approaches, it is usually not enough to understand the type of errors committed by the system.Purity and coverage are two dual evaluation metrics that provide additional insight on the behavior of the system.

A hypothesized annotation has perfect purity if all of its labels overlap only segments which are members of a single reference label. Similarly, A hypothesized annotation has perfect coverage if all segments from a given reference label are clustered in the same cluster.

Over-segmented results (e.g. too many speaker clusters) tend to lead to high purity and low coverage, while under-segmented results (e.g. when two speakers are merged into one large cluster) lead to low purity and higher coverage.

## More info in reference
* http://pyannote.github.io/pyannote-metrics/reference.html#evaluation-metrics
