## Getting Started

This project is Speechmatics' fork of https://github.com/pyannote/pyannote-metrics used to calculate various speaker diarization metrics from reference/hypothesis transcript pairs.

This package has a CLI supporting ctm, lab, or V2 JSON format transcripts and can be run using eg
`python3 -m sm_diarisation_metrics.cookbook reference.json transcript.json`

### Run from source code

If you would prefer to clone the repo and run the source code: 
`git clone git@github.com:speechmatics/speechmatics-python.git`
`cd speechmatics-python/metrics/sm_diarization_metrics`
`pip install -r ./requirements.txt`
`python3 -m sm_diarization_metrics.cookbook reference.json transcript.json` 
``

### Build wheel
To build and install the wheel run:

$ make wheel
$ make install

### Docs

A description of each of the metrics is available in sm_diarization_metrics.pdf

