"""Entrypoint for SM metrics"""

import argparse
import sys

try:
    import asr_metrics.wer.__main__ as wer_metrics

    WER_AVAILABLE = True
except ImportError:
    WER_AVAILABLE = False

try:
    import asr_metrics.diarization.sm_diarization_metrics.cookbook as diarization_metrics

    DIARIZATION_AVAILABLE = True
except ImportError:
    DIARIZATION_AVAILABLE = False


def main():
    parser = argparse.ArgumentParser(
        description="Speechmatics metrics tool for WER and diarization"
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="mode", help="Metrics mode. Choose from 'wer' or 'diarization'"
    )
    subparsers.required = True  # Make sure a subparser is always provided

    if WER_AVAILABLE:
        wer_parser = subparsers.add_parser("wer", help="Entrypoint for WER metrics")
        wer_metrics.get_wer_args(wer_parser)
    else:
        wer_parser = subparsers.add_parser(
            "wer", help="Entrypoint for WER metrics (requires additional dependencies)"
        )

    if DIARIZATION_AVAILABLE:
        diarization_parser = subparsers.add_parser(
            "diarization", help="Entrypoint for diarization metrics"
        )
        diarization_metrics.get_diarization_args(diarization_parser)
    else:
        diarization_parser = subparsers.add_parser(
            "diarization",
            help="Entrypoint for diarization metrics (requires pyannote dependencies)",
        )
        diarization_parser.add_argument(
            "--help-install",
            action="store_true",
            help="Show instructions for installing diarization dependencies",
        )

    args = parser.parse_args()

    if args.mode == "wer":
        if WER_AVAILABLE:
            wer_metrics.main(args)
        else:
            print("Error: WER metrics require additional dependencies.")
            print("Please install them with: pip install speechmatics-python[metrics]")
            sys.exit(1)
    elif args.mode == "diarization":
        if DIARIZATION_AVAILABLE:
            diarization_metrics.main(args)
        else:
            print("Error: Diarization metrics require additional dependencies.")
            print("Please install them with: pip install speechmatics-python[metrics]")
            sys.exit(1)
    else:
        print("Unsupported mode. Please use 'wer' or 'diarization'")


if __name__ == "__main__":
    main()
