# SM Diarisation Metrics

## Getting Started

This project is Speechmatics' fork of https://github.com/pyannote/pyannote-metrics used to calculate various speaker diarization metrics from reference/hypothesis transcript pairs.

### Run from PyPI

```
pip install speechmatics-python
```

This package has a CLI supporting ctm, lab, or V2 JSON format transcripts and can be run using:

```bash
sm-metrics diarization <reference file> <hypothesis file>
```

For further guidance run:

```
sm-metrics diarization -h
```

### Run from source code

If you would prefer to clone the repo and run the source code, that can be done as follows.

Clone the repository and install package:
```bash
git clone https://github.com/speechmatics/speechmatics-python.git && cd speechmatics-python && python setup.py install
```

And run directly:
```
python3 -m metrics.cli <reference file> <transcript_file>
```



## Permitted Formats

### CTM

Plain text file with the '.ctm' extension. Each line is of the form:
```
<file id> <speaker> <start time> <end time> <word> <confidence>
```

### LAB

Plain text file with the '.lab' extension. Each line is of the form:
```
<start time> <end time> <speaker>
```

### JSON (Diarisation Reference format)

JSON file of the form:

```json
[
    {
        "speaker_name": "Speaker 1",
        "word": "Seems",
        "start": 0.75,
        "duration": 0.29
    },
]

```

### JSON (Speechmatics ASR Output)

V2 JSON output of Speechmatics ASR can be directly used as a hypothesis for diarization metrics

## Docs

Further description of how to use the tool and the metrics available are in sm_diarization_metrics.pdf

When using the PDF, be aware that it assumes you are running the source code directly from `./metrics/diarization`
