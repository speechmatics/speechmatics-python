import speechmatics
import speechmatics.models
import speechmatics.client
import speechmatics.cli
import asyncio
import argparse
import sys
import sounddevice as sd


class RawInputStreamWrapper:
    def __init__(self, wrapped: sd.RawInputStream):
        self.wrapped: sd.RawInputStream = wrapped

    def read(self, frames):
        return bytes(self.wrapped.read(frames)[0])


async def transcribe_from_device(device, speechmatics_client, language: str, max_delay):
    frame_rate = 44_100
    with sd.RawInputStream(
        device=device, channels=1, samplerate=frame_rate, dtype="float32"
    ) as stream:
        settings = speechmatics.models.AudioSettings(
            sample_rate=frame_rate,
            encoding="pcm_f32" + ("le" if sys.byteorder == "little" else "be"),
        )

        conf = speechmatics.models.TranscriptionConfig(
            language=language,
            operating_point="enhanced",
            max_delay=max_delay,
            enable_partials=True,
            enable_entities=True,
        )
        await speechmatics_client.run(
            transcription_config=conf,
            stream=RawInputStreamWrapper(stream),
            audio_settings=settings,
        )


def main(args):
    speechmatics_client = speechmatics.client.WebsocketClient(
        connection_settings_or_auth_token=args.auth_token
    )
    transcripts = speechmatics.cli.Transcripts(text="", json=[])
    speechmatics.cli.add_printing_handlers(speechmatics_client, transcripts)

    asyncio.run(
        transcribe_from_device(
            args.device, speechmatics_client, args.language, args.max_delay
        )
    )


def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Speechmatics Microphone Realtime Transcription example"
    )
    parser.add_argument(
        "-d", "--device", type=int_or_str, help="input device (numeric ID or substring)"
    )
    parser.add_argument("-a", "--auth_token", type=str, required=True)
    parser.add_argument("-l", "--language", type=str, default="en")
    parser.add_argument("-m", "--max_delay", type=float, default=2.0)

    main(parser.parse_args())
