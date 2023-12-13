# SM Metrics

We provide some additional tooling to help benchmark transcription and diarization performance.

## Getting Started

### CLI

The `sm-metrics` binary is built after installing with PyPI or running `python3 setup.py install` from the source code. To see the options from the command-line, use the following:
``` bash
sm-metrics -h
```

### Source Code

When executing directly from the source code:
```bash
python3 -m metrics.cli -h
```

## What's Included?

### Transcription Metrics

This includes tools to:
- Normalise transcripts
- Calculate Word Error Rate and Character Error Rate
- Calculate the number of substitutions, deletions and insertions for a given ASR transcript
- Visualise the alignment and differences between a reference and ASR transcript

### Diarization Metrics

This includes tools to calculate a number of metrics used in benchmarking diarization, including:

- Diarization Error Rate
- Segmentation precision, recall and F1-Scores
- Word Diarization Error Rate

## Documentation

More extensive information on the metrics themselves, as well as how to run them can be found on the READMEs.

For diarization, we provide an additional PDF.

## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com or raise an issue for this repo.
