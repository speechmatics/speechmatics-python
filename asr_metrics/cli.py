"""Entrypoint for SM metrics"""
import argparse

import asr_metrics.diarization.sm_diarization_metrics.cookbook as diarization_metrics
import asr_metrics.wer.__main__ as wer_metrics


def main():
    parser = argparse.ArgumentParser(description="Your CLI description")

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="mode", help="Metrics mode. Choose from 'wer' or 'diarization'"
    )
    subparsers.required = True  # Make sure a subparser id always provided

    wer_parser = subparsers.add_parser("wer", help="Entrypoint for WER metrics")
    wer_metrics.get_wer_args(wer_parser)

    diarization_parser = subparsers.add_parser(
        "diarization", help="Entrypoint for diarization metrics"
    )
    diarization_metrics.get_diarization_args(diarization_parser)

    args = parser.parse_args()

    if args.mode == "wer":
        wer_metrics.main(args)
    elif args.mode == "diarization":
        diarization_metrics.main(args)
    else:
        print("Unsupported mode. Please use 'wer' or 'diarization'")


if __name__ == "__main__":
    main()
