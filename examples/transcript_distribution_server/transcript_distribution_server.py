import asyncio
import json
import logging
import os
import re
import subprocess
import time
from argparse import ArgumentParser
from collections import deque
from dataclasses import dataclass, field
from functools import partial
from typing import Dict, List, Tuple

import websockets

from speechmatics.client import WebsocketClient
from speechmatics.models import (
    AudioSettings,
    ConnectionSettings,
    ServerMessageType,
    TranscriptionConfig,
)

AUTH_TOKEN = os.environ["AUTH_TOKEN"]
CONNECTION_URL = "wss://eu2.rt.speechmatics.com/v2/en"

LOGGER = logging.getLogger("server")

FRAME_RATE = 16000
FFMPEG_OUTPUT_FORMAT = "f32le"
ENCODING = f"pcm_{FFMPEG_OUTPUT_FORMAT}"
SECONDS_BEFORE_CLOSING = 10

settings = AudioSettings(encoding=ENCODING, sample_rate=FRAME_RATE)


@dataclass
class StreamState:
    internal_task: asyncio.Task
    connections: List = field(default_factory=list)
    previous_messages: deque = field(default_factory=partial(deque, maxlen=20))


STREAMS: Dict[Tuple[str, str], StreamState] = {}


async def log_stderr(process):
    ffmpeg_logger = logging.getLogger("FFMPEG")
    while True:
        line = (await process.stderr.readline()).decode("utf-8")
        if len(line) == 0:
            break
        ffmpeg_logger.error(line)


def send_transcript(message, stream_url, language, start_time):
    if (stream_url, language) not in STREAMS:
        # no clients to serve
        logging.error("No clients to serve")
        return

    message["current_timestamp"] = time.time()

    message["metadata"]["transcript"] = (
        str(message["metadata"]["transcript"]).lstrip(".,?! ").rstrip()
    )
    message["metadata"]["epoch_start_time"] = (
        message["metadata"]["start_time"] + start_time
    )
    message["metadata"]["epoch_end_time"] = message["metadata"]["end_time"] + start_time
    stream_state = STREAMS[(stream_url, language)]

    stream_state.previous_messages.append(message)
    LOGGER.debug(f"Received {message} for {stream_url}")

    LOGGER.info(
        f"Broadcasting message for {stream_url} ({language}) to {len(stream_state.connections)} clients"
    )
    # pylint: disable=no-member
    websockets.broadcast(stream_state.connections, json.dumps(message))


def finish_session(message, stream_url, language):
    LOGGER.info(f"Received end of transcript: {message}")
    if (stream_url, language) not in STREAMS:
        # no clients to serve
        return
    stream_state = STREAMS[(stream_url, language)]
    loop = asyncio.get_event_loop()
    for connection in stream_state.connections:
        loop.create_task(connection.close())


async def load_stream(stream_url: str, language: str):
    LOGGER.info(f"loading stream {stream_url} in language {language}")
    conf = TranscriptionConfig(
        language=language,
        enable_partials=False,
        operating_point="enhanced",
        max_delay=5,
    )

    stream_with_arg = (
        f"{stream_url}?rcvbuf=15000000"
        if stream_url.startswith("srt://")
        else stream_url
    )
    ffmpegs_args = [
        # *("-v", "48"),
        *("-i", stream_with_arg),
        *("-f", FFMPEG_OUTPUT_FORMAT),
        *("-ar", FRAME_RATE),
        *("-ac", 1),
        *("-acodec", ENCODING),
        "-",
    ]
    LOGGER.info(f"Running ffmpeg with args: {ffmpegs_args}")
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        *map(str, ffmpegs_args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    LOGGER.info("ffmpeg started")
    if "srt://" in stream_url:
        while True:
            line = (await process.stderr.readline()).decode("utf-8")
            if "start" in line:
                match = re.search(r"start: ([\d.]*)", line)
                if match is not None:
                    start_time = float(match.group(1))
                    LOGGER.info(f"Starting stream at {start_time}")
                else:
                    raise ValueError("can't parse start time")
                break
    start_time = time.time()
    sm_client = WebsocketClient(
        ConnectionSettings(
            url=CONNECTION_URL,
            auth_token=AUTH_TOKEN,
            generate_temp_token=True,
        )
    )
    sm_client.add_event_handler(
        event_name=ServerMessageType.AddTranscript,
        event_handler=partial(
            send_transcript,
            stream_url=stream_url,
            language=language,
            start_time=start_time,
        ),
    )
    sm_client.add_event_handler(
        event_name=ServerMessageType.EndOfTranscript,
        event_handler=partial(finish_session, stream_url=stream_url, language=language),
    )
    asr_task = asyncio.create_task(sm_client.run(process.stdout, conf, settings))
    LOGGER.info("Starting transcription")
    log_task = asyncio.create_task(log_stderr(process))
    try:
        await asyncio.wait([log_task, asr_task], return_when=asyncio.FIRST_EXCEPTION)
    except asyncio.CancelledError:
        sm_client.stop()
        process.kill()
        asr_task.cancel()
        await asr_task
        LOGGER.info("Cancelled")
    LOGGER.info("Finished transcription")


async def close_stream_with_delay(key):
    stream_state = STREAMS[key]
    if len(stream_state.connections) > 0:
        return

    await asyncio.sleep(SECONDS_BEFORE_CLOSING)
    if len(stream_state.connections) > 0:
        return

    LOGGER.info("No connections left. Closing transcription")
    stream_state.internal_task.cancel()
    STREAMS.pop(key)
    await stream_state.internal_task


async def ws_handler(websocket):
    LOGGER.info("Client connected")
    await websocket.send(
        json.dumps(
            {
                "message": "Initialised",
                "info": "Waiting for message specifing desired stream url",
            }
        )
    )
    stream_data = json.loads(await websocket.recv())
    LOGGER.info(f"Received stream connection data {stream_data}")
    stream_url = stream_data["url"]
    stream_language = stream_data.get("language", "en")
    stream_key = (stream_url, stream_language)

    if stream_key in STREAMS:
        LOGGER.info(f"{stream_url} already started.")
        STREAMS[stream_key].connections.append(websocket)
        for old_message in STREAMS[stream_key].previous_messages:
            await websocket.send(json.dumps(old_message))
    else:
        LOGGER.info(f"Creating a new Transcription session for {stream_url}")
        STREAMS[stream_key] = StreamState(
            internal_task=asyncio.create_task(load_stream(stream_url, stream_language)),
            connections=[websocket],
        )

    try:
        await websocket.wait_closed()
    finally:
        logging.info("Connection closed, cleaning up")
        if stream_key in STREAMS:
            stream_state = STREAMS[stream_key]
            stream_state.connections.remove(websocket)
            await close_stream_with_delay(stream_key)


async def main(port):
    LOGGER.info("Starting WebSocket Server")
    # pylint: disable=no-member
    async with websockets.serve(ws_handler, "0.0.0.0", port):
        await asyncio.Future()  # Wait forever


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--port", default=8765, type=int, help="Port for the Websocket server"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "info").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main(args.port))
