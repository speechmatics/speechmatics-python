# (c) 2020, Cantab Research Ltd.
"""
Wrapper library to interface with Real-time ASR v2 API.
Based on http://asyncio.readthedocs.io/en/latest/producer_consumer.html
"""

import asyncio
import copy
import json
import logging
import sys
import traceback

import websockets

from speechmatics.exceptions import EndOfTranscriptException, \
    TranscriptionError
from speechmatics.models import ClientMessageType, ServerMessageType
from speechmatics.helpers import json_utf8, read_in_chunks, call_middleware


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

    def __init__(self, connection_settings):
        self.connection_settings = connection_settings
        self.websocket = None
        self.transcription_config = None

        self.event_handlers = {x: [] for x in ServerMessageType}
        self.middlewares = {x: [] for x in ClientMessageType}

        self.seq_no = 0
        self.session_running = False
        self._transcription_config_needs_update = False
        self._session_needs_closing = False

        # The following asyncio fields are fully instantiated in
        # _init_synchronization_primitives
        self._recognition_started = asyncio.Event
        # Semaphore used to ensure that we don't send too much audio data to
        # the server too quickly and burst any buffers downstream.
        self._buffer_semaphore = asyncio.BoundedSemaphore

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

    @json_utf8
    def _set_recognition_config(self):
        """
        Constructs a
        :py:attr:`speechmatics.models.ClientMessageType.SetRecognitionConfig`
        message.
        """
        msg = {
            "message": ClientMessageType.SetRecognitionConfig,
            "transcription_config": self.transcription_config.asdict(),
        }
        call_middleware(
            self.middlewares, ClientMessageType.SetRecognitionConfig,
            msg, False
        )
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
        msg = {
            "message": ClientMessageType.StartRecognition,
            "audio_format": audio_settings.asdict(),
            "transcription_config": self.transcription_config.asdict(),
        }
        self.session_running = True
        call_middleware(
            self.middlewares, ClientMessageType.StartRecognition, msg, False
        )
        LOGGER.debug(msg)
        return msg

    @json_utf8
    def _end_of_stream(self):
        """
        Constructs an
        :py:attr:`speechmatics.models.ClientMessageType.EndOfStream`
        message.
        """
        msg = {
            "message": ClientMessageType.EndOfStream,
            "last_seq_no": self.seq_no
        }
        call_middleware(
            self.middlewares, ClientMessageType.EndOfStream, msg, False)
        LOGGER.debug(msg)
        return msg

    def _consumer(self, message):
        """
        Consumes messages and acts on them.

        :param message: Message received from the server.
        :type message: str

        :raises TranscriptionError: on an error message received from the
            server.
        :raises EndOfTranscriptException: on EndOfTranscription message.
        """
        LOGGER.debug(message)
        message = json.loads(message)
        message_type = message["message"]

        for handler in self.event_handlers[message_type]:
            handler(copy.deepcopy(message))

        if message_type == ServerMessageType.RecognitionStarted:
            self._flag_recognition_started()
        elif message_type == ServerMessageType.AudioAdded:
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
            self.seq_no += 1
            call_middleware(
                self.middlewares, ClientMessageType.AddAudio, audio_chunk, True
            )
            yield audio_chunk

        yield self._end_of_stream()

    async def _consumer_handler(self):
        """
        Controls the consumer loop for handling messages from the server.
        """
        while self.session_running:
            message = await self.websocket.recv()
            self._consumer(message)

    async def _producer_handler(self, stream, audio_chunk_size):
        """
        Controls the producer loop for sending messages to the server.
        """
        await self._recognition_started.wait()
        async for message in self._producer(stream, audio_chunk_size):
            await self.websocket.send(message)

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

    async def run(self, stream, transcription_config, audio_settings):
        """
        Begin a new recognition session.
        This will run asynchronously. Most callers may prefer to use
        :py:meth:`run_synchronously` which will block until the session is
        finished.

        :param stream: File-like object which an audio stream can be read from.
        :type stream: io.IOBase

        :param transcription_config: Configuration for the transcription.
        :type transcription_config: speechmatics.models.TranscriptionConfig

        :param audio_settings: Configuration for the audio stream.
        :type audio_settings: speechmatics.models.AudioSettings

        :raises Exception: Can raise any exception returned by the
            consumer/producer tasks.
        """
        self.transcription_config = transcription_config
        self.seq_no = 0
        await self._init_synchronization_primitives()

        extra_headers = dict()
        if self.connection_settings.auth_token is not None:
            token = f"Bearer {self.connection_settings.auth_token}"
            extra_headers["Authorization"] = token

        try:
            websocket = await websockets.connect(  # pylint: disable=no-member
                self.connection_settings.url,
                ssl=self.connection_settings.ssl_context,
                ping_timeout=self.connection_settings.ping_timeout_seconds,
                # Don't artificially limit the max. size of incoming messages
                max_size=None,
                extra_headers=extra_headers,
            )
        except ConnectionResetError:
            traceback.print_exc()
            LOGGER.error(
                "Caught ConnectionResetError when attempting to connect to "
                "server. The most likely reason for this is that the client "
                "has been configured to use SSL but the server does not "
                "support SSL. If this is the case then try using "
                "--ssl-mode=none"
            )
            sys.exit(1)

        self.websocket = websocket
        start_recognition_msg = self._start_recognition(audio_settings)
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
            if exc and not isinstance(exc, EndOfTranscriptException):
                raise exc

        await websocket.close()

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
        """
        # pylint: disable=no-value-for-parameter
        asyncio.run(
            asyncio.wait_for(self.run(*args, **kwargs), timeout=timeout))
