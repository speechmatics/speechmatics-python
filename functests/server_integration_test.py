#!/usr/bin/env python3
import os
import unittest

from tenacity import retry, stop_after_attempt, wait_fixed, \
    retry_if_exception_type

from speechmatics.client import WebsocketClient, TranscriptionError
from speechmatics.models import TranscriptionConfig, AudioSettings

URL_OF_RUNNING_SERVER = "wss://localhost:9000/v2"
PATH_HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_FILE_PATH = os.path.join(PATH_HERE, "8kHz_short_text.wav")


class IntegrationTests(unittest.TestCase):
    # These tests can fail when the rt server has only one worker, because one
    # test can end and another immediately starts before the worker is ready.
    # So we retry them with a small delay between attempts to avoid this.
    standard_retry = retry(
        wait=wait_fixed(1),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(TranscriptionError),
    )

    @standard_retry
    @staticmethod
    def test_stream_a_small_file():
        """
        This test streams a file into the real time api in the simplest way
        possible.
        """
        audio_file = open(EXAMPLE_FILE_PATH, "rb")
        api = WebsocketClient(url=URL_OF_RUNNING_SERVER)

        transcription_config = TranscriptionConfig("en")
        audio_settings = AudioSettings(sample_rate=8000)
        api.run_synchronously(
            audio_file, transcription_config, audio_settings, insecure=True
        )

    @standard_retry
    @staticmethod
    def test_partials():
        """This test prints partial transcriptions to stdout."""
        audio_file = open(EXAMPLE_FILE_PATH, "rb")
        api = WebsocketClient(url=URL_OF_RUNNING_SERVER)

        transcription_config = TranscriptionConfig("en", enable_partials=True)
        audio_settings = AudioSettings(sample_rate=8000)
        api.run_synchronously(
            audio_file, transcription_config, audio_settings, insecure=True
        )


if __name__ == "__main__":
    unittest.main()
