# (c) 2020, Cantab Research Ltd.
"""
Wrapper library to interface with Real-time ASR v2 API.
Based on http://asyncio.readthedocs.io/en/latest/producer_consumer.html
"""

import asyncio
import base64
from collections import defaultdict
from contextlib import AsyncExitStack
import copy
from io import IOBase
import json
import logging
import os
from typing import Any, Dict, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
import websockets

from speechmatics.exceptions import (
    EndOfTranscriptException,
    ForceEndSession,
    TranscriptionError,
)
from speechmatics.helpers import (
    check_tasks_exceptions,
    get_version,
    json_utf8,
    read_in_chunks,
)
from speechmatics.models import (
    AudioSettings,
    ClientMessageType,
    ConnectionSettings,
    ServerMessageType,
    TranscriptionConfig,
    UsageMode,
)

try:
    # Try to import from new websockets >=13.0
    from websockets.asyncio.client import connect

    WS_HEADERS_KEY = "additional_headers"
except ImportError:
    # Fall back to legacy websockets
    from websockets.legacy.client import connect

    WS_HEADERS_KEY = "extra_headers"


LOGGER = logging.getLogger(__name__)

# If the logging level is set to DEBUG then websockets logs very verbosely,
# including a hex dump of every message being sent. Setting the websockets
# logger at INFO level specifically prevents this spam.
logging.getLogger("websockets.protocol").setLevel(logging.INFO)


class WebsocketClient:
    """
    Manage a transcription session with the server.

    The best way to interact with this library is to instantiate this client
    and then add a set of handlers to it. Handlers respond to particular types
    of messages received from the server.

    :param connection_settings: Settings for the WebSocket connection,
        including the URL of the server.
    :type connection_settings: speechmatics.models.ConnectionSettings
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        connection_settings_or_auth_token: Union[str, ConnectionSettings, None] = None,
    ):
        """
        Args:
            connection_settings_or_auth_token (Union[str, ConnectionSettings, None], optional): Defaults to None.
                If `str`,, assumes auth_token passed and default URL being used
                If `None`, attempts using auth_token from config.
        """
        if not isinstance(connection_settings_or_auth_token, ConnectionSettings):
            self.connection_settings = ConnectionSettings.create(
                UsageMode.RealTime, connection_settings_or_auth_token
            )
        else:
            self.connection_settings = connection_settings_or_auth_token
            self.connection_settings.set_missing_values_from_config(UsageMode.RealTime)
        self.websocket = None
        self.transcription_config = None

        self.event_handlers = {x: [] for x in ServerMessageType}
        self.middlewares = {x: [] for x in ClientMessageType}

        self.seq_no: defaultdict = defaultdict(int)
        self.session_running = False
        self._language_pack_info = None
        self._transcription_config_needs_update = False
        self._session_needs_closing = False
        self.channel_stream_pairs = None

        # The following asyncio fields are fully instantiated in
        # _init_synchronization_primitives
        self._recognition_started: asyncio.Event
        # Semaphore used to ensure that we don't send too much audio data to
        # the server too quickly and burst any buffers downstream.
        self._buffer_semaphore: asyncio.BoundedSemaphore

    async def _init_synchronization_primitives(self):
        """
        Used to initialise synchronization primitives that require
        an event loop
        """
        self._recognition_started = asyncio.Event()
        self._buffer_semaphore = asyncio.BoundedSemaphore(
            self.connection_settings.message_buffer_size
        )

    def _flag_recognition_started(self):
        """
        Handle a
        :py:attr:`speechmatics.models.ClientMessageType.SetRecognitionConfig`
        message from the server.
        This updates an internal flag to mark the recognition session
        as started meaning, AddAudio is now allowed.
        """
        self._recognition_started.set()

    def _set_language_pack_info(self, language_pack_info: dict):
        """
        Update the `language_pack_info` which is a subset of information from the
        manifest in the language pack which we expose to end users via the
        RecognitionStarted message.
        """
        self._language_pack_info = language_pack_info

    def get_language_pack_info(self) -> dict:
        """
        Get the `language_pack_info` which is a subset of information from the
        manifest in the language pack which we expose to end users.

        Can be None if this field has not yet been set - i.e. if the RecognitionStarted
        message has not been received yet.
        """
        return self._language_pack_info

    @json_utf8
    def _set_recognition_config(self):
        """
        Constructs a
        :py:attr:`speechmatics.models.ClientMessageType.SetRecognitionConfig`
        message.
        """
        assert self.transcription_config is not None
        msg = {
            "message": ClientMessageType.SetRecognitionConfig,
            "transcription_config": self.transcription_config.as_config(),
        }
        if self.transcription_config.translation_config is not None:
            msg["translation_config"] = (
                self.transcription_config.translation_config.asdict()
            )
        if self.transcription_config.audio_events_config is not None:
            msg["audio_events_config"] = (
                self.transcription_config.audio_events_config.asdict()
            )
        self._call_middleware(ClientMessageType.SetRecognitionConfig, msg, False)
        return msg

    @json_utf8
    def _start_recognition(self, audio_settings):
        """
        Constructs a
        :py:attr:`speechmatics.models.ClientMessageType.StartRecognition`
        message.
        This initiates the recognition session.

        :param audio_settings: Audio settings to use.
        :type audio_settings: speechmatics.models.AudioSettings
        """
        assert self.transcription_config is not None
        msg = {
            "message": ClientMessageType.StartRecognition,
            "audio_format": audio_settings.asdict(),
            "transcription_config": self.transcription_config.as_config(),
        }

        if self.transcription_config.translation_config is not None:
            msg["translation_config"] = (
                self.transcription_config.translation_config.asdict()
            )
        if self.transcription_config.audio_events_config is not None:
            msg["audio_events_config"] = (
                self.transcription_config.audio_events_config.asdict()
            )
        self.session_running = True
        self._call_middleware(ClientMessageType.StartRecognition, msg, False)
        LOGGER.debug(msg)
        return msg

    @json_utf8
    def _end_of_stream(self):
        """
        Constructs an
        :py:attr:`speechmatics.models.ClientMessageType.EndOfStream`
        message.
        """
        assert (
            self.channel_stream_pairs is None
        ), "End of stream can only be sent for a single channel"
        seq_no = 0
        # if client disconnects before sending any audio, seq_no will be empty
        if len(self.seq_no) == 1:
            seq_no = next(iter(self.seq_no.values()))
        msg = {"message": ClientMessageType.EndOfStream, "last_seq_no": seq_no}
        self._call_middleware(ClientMessageType.EndOfStream, msg, False)
        LOGGER.debug(msg)
        return msg

    def _end_of_channel(self, channel: str) -> dict:
        """
        Constructs a :py:attr:`speechmatics.models.ClientMessageType.EndOfChannel` message.

        :param channel: The name of the channel for which the end message is being constructed.
        :type channel: str
        """
        msg = {
            "message": ClientMessageType.EndOfChannel,
            "channel": channel,
            "last_seq_no": self.seq_no[channel],
        }
        self._call_middleware(ClientMessageType.EndOfChannel, msg, False)
        LOGGER.debug(msg)
        return msg

    def _consumer(self, message):
        """
        Consumes messages and acts on them.

        :param message: Message received from the server.
        :type message: str

        :raises TranscriptionError: on an error message received from the
            server after the Session started.
        :raises EndOfTranscriptException: on EndOfTranscription message.
        :raises ForceEndSession: If this was raised by the user's event
            handler.
        """
        LOGGER.debug(f"{message=}")
        message = json.loads(message)
        message_type = message["message"]

        for handler in self.event_handlers[message_type]:
            try:
                handler(copy.deepcopy(message))
            except ForceEndSession:
                LOGGER.warning("Session was ended forcefully by an event handler")
                raise

        if message_type == ServerMessageType.RecognitionStarted:
            self._flag_recognition_started()
            if "language_pack_info" in message:
                self._set_language_pack_info(message["language_pack_info"])
        elif message_type == ServerMessageType.AudioAdded:
            self._buffer_semaphore.release()
        elif message_type == ServerMessageType.ChannelAudioAdded:
            self._buffer_semaphore.release()
        elif message_type == ServerMessageType.EndOfTranscript:
            raise EndOfTranscriptException()
        elif message_type == ServerMessageType.Warning:
            LOGGER.warning(message["reason"])
        elif message_type == ServerMessageType.Error:
            raise TranscriptionError(message["reason"])

    async def _producer(self, stream, audio_chunk_size):
        """
        Yields messages to send to the server.

        :param stream: File-like object which an audio stream can be read from.
        :type stream: io.IOBase

        :param audio_chunk_size: Size of audio chunks to send.
        :type audio_chunk_size: int
        """
        if self.channel_stream_pairs is not None:
            async for msg in self._process_multichannel_streams(audio_chunk_size):
                yield msg
        else:
            async for msg in self._process_single_stream(stream, audio_chunk_size):
                yield msg

    async def _stream_channel(self, channel, stream, queue, audio_chunk_size):
        """
        Stream audio data for a specific channel and put messages into the queue.
        """
        async for audio_chnk in read_in_chunks(stream, audio_chunk_size):
            if self._session_needs_closing:
                break
            if self._transcription_config_needs_update:
                await queue.put(self._set_recognition_config())
                self._transcription_config_needs_update = False
            await asyncio.wait_for(
                self._buffer_semaphore.acquire(),
                timeout=self.connection_settings.semaphore_timeout_seconds,
            )

            base64_chunk = base64.b64encode(audio_chnk).decode("utf-8")
            message = {
                "message": "AddChannelAudio",
                "channel": channel,
                "data": base64_chunk,
            }

            # seq_no is defaultdict is so the keys are created automatically
            self.seq_no[channel] += 1
            self._call_middleware(ClientMessageType.AddChannelAudio, message, False)
            await queue.put(message)
        await queue.put(self._end_of_channel(channel))

    async def _process_multichannel_streams(self, audio_chunk_size):
        """
        Process multiple channel streams and yield messages to send to the server.
        """
        assert (
            self.channel_stream_pairs is not None
        ), "Channel stream pairs must be set for multichannel mode"
        queue = asyncio.Queue()
        tasks = [
            asyncio.create_task(
                self._stream_channel(channel, channel_stream, queue, audio_chunk_size)
            )
            for channel, channel_stream in self.channel_stream_pairs.items()
        ]
        while True:
            check_tasks_exceptions(tasks)
            streams_done = all(task.done() for task in tasks)
            if streams_done and queue.empty():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield json.dumps(message)
            except asyncio.TimeoutError:
                continue

    async def _process_single_stream(self, stream, audio_chunk_size):
        """
        Process a single channel stream and yield messages to send to the server.
        Yields binary audio chunks
        """
        async for audio_chunk in read_in_chunks(stream, audio_chunk_size):
            if self._session_needs_closing:
                break

            if self._transcription_config_needs_update:
                yield self._set_recognition_config()
                self._transcription_config_needs_update = False

            await asyncio.wait_for(
                self._buffer_semaphore.acquire(),
                timeout=self.connection_settings.semaphore_timeout_seconds,
            )
            self.seq_no["single"] += 1
            self._call_middleware(ClientMessageType.AddAudio, audio_chunk, True)
            yield audio_chunk

        yield self._end_of_stream()

    async def _consumer_handler(self):
        """
        Controls the consumer loop for handling messages from the server.

        raises: ConnectionClosedError when the upstream closes unexpectedly
        """
        while self.session_running:
            try:
                message = await self.websocket.recv()
            except websockets.exceptions.ConnectionClosedOK:
                # Can occur if a timeout has closed the connection.
                LOGGER.info("Cannot receive from closed websocket.")
                return
            except websockets.exceptions.ConnectionClosedError as ex:
                LOGGER.info("Disconnected while waiting for recv().")
                raise ex
            self._consumer(message)

    async def _producer_handler(self, stream, audio_chunk_size):
        """
        Controls the producer loop for sending messages to the server.
        """
        await self._recognition_started.wait()
        async for message in self._producer(stream, audio_chunk_size):
            try:
                await self.websocket.send(message)
            except websockets.exceptions.ConnectionClosedOK:
                # Can occur if a timeout has closed the connection.
                LOGGER.info("Cannot send from a closed websocket.")
                return
            except websockets.exceptions.ConnectionClosedError:
                LOGGER.info("Disconnected while sending a message().")
                return

    def _call_middleware(self, event_name, *args):
        """
        Call the middlewares attached to the client for the given event name.

        :raises ForceEndSession: If this was raised by the user's middleware.
        """
        for middleware in self.middlewares[event_name]:
            try:
                middleware(*args)
            except ForceEndSession:
                LOGGER.warning("Session was ended forcefully by a middleware")
                raise

    def update_transcription_config(self, new_transcription_config):
        """
        Updates the transcription config used for the session.
        This results in a SetRecognitionConfig message sent to the server.

        :param new_transcription_config: The new config object.
        :type new_transcription_config: speechmatics.models.TranscriptionConfig
        """
        if new_transcription_config != self.transcription_config:
            self.transcription_config = new_transcription_config
            self._transcription_config_needs_update = True

    def add_event_handler(self, event_name, event_handler):
        """
        Add an event handler (callback function) to handle an incoming
        message from the server. Event handlers are passed a copy of the
        incoming message from the server. If `event_name` is set to 'all' then
        the handler will be added for every event.

        For example, a simple handler that just prints out the
        :py:attr:`speechmatics.models.ServerMessageType.AddTranscript`
        messages received:

        >>> client = WebsocketClient(
                ConnectionSettings(url="wss://localhost:9000"))
        >>> handler = lambda msg: print(msg)
        >>> client.add_event_handler(ServerMessageType.AddTranscript, handler)

        :param event_name: The name of the message for which a handler is
                being added. Refer to
                :py:class:`speechmatics.models.ServerMessageType` for a list
                of the possible message types.
        :type event_name: str

        :param event_handler: A function to be called when a message of the
            given type is received.
        :type event_handler: Callable[[dict], None]

        :raises ValueError: If the given event name is not valid.
        """
        if event_name == "all":
            for name in self.event_handlers.keys():
                self.event_handlers[name].append(event_handler)
        elif event_name not in self.event_handlers:
            raise ValueError(
                f"Unknown event name: {event_name!r}, expected to be "
                f"'all' or one of {list(self.event_handlers.keys())}."
            )
        else:
            self.event_handlers[event_name].append(event_handler)

    def add_middleware(self, event_name, middleware):
        """
        Add a middleware to handle outgoing messages sent to the server.
        Middlewares are passed a reference to the outgoing message, which
        they may alter.
        If `event_name` is set to 'all' then the handler will be added for
        every event.

        :param event_name: The name of the message for which a middleware is
            being added. Refer to the V2 API docs for a list of the possible
            message types.
        :type event_name: str

        :param middleware: A function to be called to process an outgoing
            message of the given type. The function receives the message as
            the first argument and a second, boolean argument indicating
            whether or not the message is binary data (which implies it is an
            AddAudio message).
        :type middleware: Callable[[dict, bool], None]

        :raises ValueError: If the given event name is not valid.
        """
        if event_name == "all":
            for name in self.middlewares.keys():
                self.middlewares[name].append(middleware)
        elif event_name not in self.middlewares:
            raise ValueError(
                (
                    f"Unknown event name: {event_name}, expected to be 'all'"
                    f"or one of {list(self.middlewares.keys())}."
                )
            )
        else:
            self.middlewares[event_name].append(middleware)

    async def _communicate(self, stream, audio_settings):
        """
        Create a producer/consumer for transcription messages and
        communicate with the server.
        Internal method called from _run.
        """
        try:
            start_recognition_msg = self._start_recognition(audio_settings)
        except ForceEndSession:
            return
        await self.websocket.send(start_recognition_msg)

        consumer_task = asyncio.create_task(self._consumer_handler())
        producer_task = asyncio.create_task(
            self._producer_handler(stream, audio_settings.chunk_size)
        )
        (done, pending) = await asyncio.wait(
            [consumer_task, producer_task], return_when=asyncio.FIRST_EXCEPTION
        )

        # If a task is pending the other one threw an exception, so tidy up
        for task in pending:
            task.cancel()

        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (EndOfTranscriptException, ForceEndSession)):
                raise exc

    async def run(
        self,
        stream: Union[IOBase, Dict[str, IOBase]],
        transcription_config: TranscriptionConfig,
        audio_settings: AudioSettings = None,
        from_cli: bool = False,
        extra_headers: Dict = None,
    ):
        """
        Begin a new recognition session.
        This will run asynchronously. Most callers may prefer to use
        :py:meth:`run_synchronously` which will block until the session is
        finished.

        :param transcription_config: Configuration for the transcription.
        :type transcription_config: speechmatics.models.TranscriptionConfig

        :param stream: Optional file-like object or Dict of file-likes which an audio stream can be read from.
        :type stream: Union[IOBase, Dict[str, IOBase]],

        :param audio_settings: Configuration for the audio stream.
        :type audio_settings: speechmatics.models.AudioSettings

        :param from_cli: Indicates whether the caller is the command-line interface or not.
        :type from_cli: bool

        :raises Exception: Can raise any exception returned by the
            consumer/producer tasks.
        """
        # Check we get either a dict or a file-like object
        channel_stream_pairs = None
        if isinstance(stream, dict):
            # Case where stream is channel stream pairs
            channel_stream_pairs = stream

        # Set channel_stream pairs if provided
        if channel_stream_pairs is not None:
            opened_streams = {}
            self._stream_exits = AsyncExitStack()
            for channel_name, path in channel_stream_pairs.items():
                if isinstance(path, str):
                    file_object = await asyncio.to_thread(open, path, "rb")
                else:
                    file_object = path
                opened_streams[channel_name] = file_object
            self.channel_stream_pairs = opened_streams
        else:
            self.channel_stream_pairs = None

        self.transcription_config = transcription_config
        self._language_pack_info = None
        await self._init_synchronization_primitives()
        if extra_headers is None:
            extra_headers = {}
        if audio_settings is None:
            audio_settings = AudioSettings()
        if (
            not self.connection_settings.generate_temp_token
            and self.connection_settings.auth_token is not None
        ):
            token = f"Bearer {self.connection_settings.auth_token}"
            extra_headers["Authorization"] = token

        if (
            self.connection_settings.generate_temp_token
            and self.connection_settings.auth_token is not None
        ):
            temp_token = await _get_temp_token(self.connection_settings)
            token = f"Bearer {temp_token}"
            extra_headers["Authorization"] = token

        url = self.connection_settings.url

        # Extend connection url with sdk version information
        cli = "-cli" if from_cli is True else ""
        version = get_version()
        parsed_url = urlparse(url)

        query_params = dict(parse_qsl(parsed_url.query))
        query_params["sm-sdk"] = f"python{cli}-{version}"
        updated_query = urlencode(query_params)

        url_path = parsed_url.path
        if not url_path.endswith(self.transcription_config.language.strip()):
            if url_path.endswith("/"):
                url_path += self.transcription_config.language.strip()
            else:
                url_path += f"/{self.transcription_config.language.strip()}"

        updated_url = urlunparse(
            parsed_url._replace(path=url_path, query=updated_query)
        )

        ws_kwargs = {
            WS_HEADERS_KEY: extra_headers,
            "ssl": self.connection_settings.ssl_context,
            "ping_timeout": self.connection_settings.ping_timeout_seconds,
            # Don't limit the max. size of incoming messages
            "max_size": None,
        }

        try:
            async with connect(
                updated_url,
                **ws_kwargs,
            ) as self.websocket:
                await self._communicate(stream, audio_settings)
        finally:
            self.session_running = False
            self._session_needs_closing = False
            self.websocket = None

    def stop(self):
        """
        Indicates that the recognition session should be forcefully stopped.
        Only used in conjunction with `run`.
        You probably don't need to call this if you're running the client via
        :py:meth:`run_synchronously`.
        """
        self._session_needs_closing = True

    def run_synchronously(self, *args, timeout=None, **kwargs):
        """
        Run the transcription synchronously.
        :raises asyncio.TimeoutError: If the given timeout is exceeded.
        """
        # pylint: disable=no-value-for-parameter
        asyncio.run(asyncio.wait_for(self.run(*args, **kwargs), timeout=timeout))

    async def send_message(self, message_type: str, data: Optional[Any] = None):
        """
        Sends a message to the server.
        """
        if not self.session_running:
            raise RuntimeError(
                "Recognition session not running. Cannot send the message."
            )

        assert self.websocket, "WebSocket not connected"

        data_ = data if data is not None else {}
        serialized_data = json.dumps({"message": message_type, **data_})
        try:
            await self.websocket.send(serialized_data)
        except websockets.exceptions.ConnectionClosedOK as exc:
            LOGGER.error("WebSocket connection is closed. Cannot send the message.")
            raise exc
        except websockets.exceptions.ConnectionClosedError as exc:
            LOGGER.error(
                "WebSocket connection closed unexpectedly while sending the message."
            )
            raise exc


async def _get_temp_token(connection_settings: ConnectionSettings):
    """
    Used to get a temporary token from management platform api for SaaS users
    """
    version = get_version()
    mp_api_url = os.getenv("SM_MANAGEMENT_PLATFORM_URL", connection_settings.mp_url)

    assert mp_api_url, "Management platform URL not set"

    endpoint = mp_api_url + "/v1/api_keys"
    params = {"type": "rt", "sm-sdk": f"python-{version}"}
    payload: dict[str, Union[str, int]] = {"ttl": 60}

    if connection_settings.region:
        payload["region"] = connection_settings.region
    if connection_settings.client_ref:
        payload["client_ref"] = connection_settings.client_ref

    headers = {
        "Authorization": f"Bearer {connection_settings.auth_token}",
        "Content-Type": "application/json",
    }
    # pylint: disable=no-member
    response = httpx.post(endpoint, json=payload, params=params, headers=headers)
    response.raise_for_status()
    response.read()
    key_object = response.json()
    return key_object["key_value"]
