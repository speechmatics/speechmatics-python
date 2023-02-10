"""
This is an example of how to use the speechmatics client to submit a batch
transcription job to our v2 batch ASR API, using BatchClient and BatchSpeakerDiarizationConfig.

It uses a short example audio file with English speech included in this directory.
"""
import logging
import os
import time
from pathlib import Path

from speechmatics.batch_client import BatchClient
from speechmatics.exceptions import JobNotFoundException
from speechmatics.models import (
    BatchTranscriptionConfig,
    BatchSpeakerDiarizationConfig,
    ConnectionSettings,
)

MY_API_KEY = os.environ["MY_API_KEY"]
API_URL = "https://eu1.asr.api.speechmatics.com/v2/"
AUDIO_FILE_PATH = str(Path(__file__).parent / "short-2-second-speech-audio.wav")


def main():
    """
    Submit a batch transcription job and wait until it finishes.
    """
    logging.basicConfig(level=logging.INFO)
    settings = ConnectionSettings(
        url=API_URL,
        auth_token=MY_API_KEY
    )
    transcription_config = BatchTranscriptionConfig(
        language="en",
        diarization="speaker",
        speaker_diarization_config=BatchSpeakerDiarizationConfig(speaker_sensitivity=0.5)
    )

    with BatchClient(settings) as client:
        logging.info("Submitting job...")
        job_id = client.submit_job(AUDIO_FILE_PATH, transcription_config)
        logging.info("Job ID is: %s", job_id)

        while True:
            logging.info("Waiting for job to finish...")

            result = None
            try:
                result = client.get_job_result(job_id)
            except JobNotFoundException:
                pass

            if result:
                print(result)
                break

            logging.info("Job not done yet.")
            time.sleep(2)


if __name__ == "__main__":
    main()
