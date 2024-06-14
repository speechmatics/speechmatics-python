import asyncio
import copy
import contextlib
import io
import json
from collections import Counter
from unittest.mock import patch, MagicMock

import asynctest
import pytest

from pytest_httpx import HTTPXMock
from speechmatics import client
from speechmatics.batch_client import BatchClient
from speechmatics.exceptions import ForceEndSession
from speechmatics.models import (
    ConnectionSettings,
    ServerMessageType,
    ClientMessageType,
    RTSpeakerDiarizationConfig,
    BatchTranscriptionConfig,
    TranscriptionConfig,
)

from tests.utils import path_to_test_resource, default_ws_client_setup


def test_json_utf8():
    @client.json_utf8
    def example():
        return {"foo": True}

    assert example() == '{"foo": true}'


async def get_chunks(stream, chunks):
    async for chunk in client.read_in_chunks(stream, 2):
        chunks.append(chunk)


def test_read_in_chunks_sync_stream():
    stream = io.BytesIO(b"\x00\x00\x00\x00\x00")
    chunks = []
    asyncio.run(asyncio.wait_for(get_chunks(stream, chunks), 10))
    assert len(chunks) == 3


def test_read_in_chunks_async_stream():
    class AsyncStream:  # pylint: disable=too-few-public-methods
        buffer = b"\x00\x00\x00\x00\x00"

        async def read(self, num_bytes):
            result, self.buffer = self.buffer[:num_bytes], self.buffer[num_bytes:]
            await asyncio.sleep(1e-5)
            return result

    chunks = []
    asyncio.run(asyncio.wait_for(get_chunks(AsyncStream(), chunks), 10))
    assert len(chunks) == 3


@pytest.mark.asyncio
async def test_read_in_chunks():
    gen = client.read_in_chunks(io.BytesIO(b"x"), 1024 * 4)
    assert await gen.__anext__() == b"x"
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    stream = io.BytesIO(bytes(range(5)))

    gen = client.read_in_chunks(stream, 2)
    assert await gen.__anext__() == b"\x00\x01"
    assert await gen.__anext__() == b"\x02\x03"
    assert await gen.__anext__() == b"\x04"
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


def test_handlers_called(mock_server, mocker):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    handlers = {}
    for msg_type in ServerMessageType:
        mock = mocker.MagicMock()
        handlers[msg_type.name] = mock
        ws_client.add_event_handler(msg_type.name, mock)

    # Add a handler for all events to test that the 'all'
    # keyword works properly.
    all_handler = mocker.MagicMock()
    ws_client.add_event_handler("all", all_handler)

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    # Each handler should have been called once for every message
    # received from the server
    server_message_counts = Counter(msg["message"] for msg in mock_server.messages_sent)
    for msg_name, count in server_message_counts.items():
        assert msg_name and handlers[msg_name].call_count == count

    # The 'all' handler should have been called for every message.
    assert all_handler.call_count == len(mock_server.messages_sent)


def test_middlewares_called(mock_server, mocker):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    middlewares = {}
    for msg_type in ClientMessageType:
        mock = mocker.MagicMock()
        middlewares[msg_type.name] = mock
        ws_client.add_middleware(msg_type.name, mock)

    # Add a middleware for all events to test that the 'all'
    # keyword works properly.
    all_handler = mocker.MagicMock()
    ws_client.add_middleware("all", all_handler)

    # Add another middleware just for StartRecognition to test that we can
    # edit values in the outgoing messages via a middleware.
    # pylint: disable=unused-argument
    def language_changing_middleware(msg, is_binary):
        msg["transcription_config"]["language"] = "ja"

    ws_client.add_middleware(
        ClientMessageType.StartRecognition, language_changing_middleware
    )

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    # Each handler should have been called once for every message
    # sent from the client
    client_message_counts = Counter(
        msg["message"] if isinstance(msg, dict) else "AddAudio"
        for msg in mock_server.messages_received
    )
    for msg_name, count in client_message_counts.items():
        assert msg_name and middlewares[msg_name].call_count == count

    # The change to the language made by the middleware above
    # should have been received
    assert (
        mock_server.find_start_recognition_message()["transcription_config"]["language"]
        == "ja"
    )  # noqa
    # The 'all' handler should have been called for every message.
    assert all_handler.call_count == len(mock_server.messages_received)


def test_force_end_session_from_event_handler(mock_server):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    def session_ender(event):
        raise ForceEndSession

    events = []
    ws_client.add_event_handler("all", events.append)
    ws_client.add_event_handler(ServerMessageType.RecognitionStarted, session_ender)

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    # Only one message should have been sent from the server
    # (which is RecognitionStarted) before the session was
    # forcefully ended.
    assert len(mock_server.messages_sent) == 1
    assert mock_server.messages_sent[0]["message"] == "RecognitionStarted"

    # The client should only have recorded one event.
    assert len(events) == 1


def test_run_synchronously_with_timeout(mock_server):
    """
    Tests that an asyncio.TimeoutError is raised if using run_synchronously
    with a very short timeout.
    """
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )
    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        with pytest.raises(asyncio.TimeoutError):
            ws_client.run_synchronously(
                audio_stream, transcription_config, audio_settings, timeout=0.0001
            )


@pytest.mark.parametrize(
    "client_message_type, expect_received_count, expect_sent_count",
    [
        pytest.param(ClientMessageType.StartRecognition, 0, 1, id="StartRecognition"),
        pytest.param(ClientMessageType.AddAudio, 1, 2, id="AddAudio"),
    ],
)
def test_force_end_session_from_middleware(
    mock_server, client_message_type, expect_received_count, expect_sent_count
):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    def session_ender(event, _):
        raise ForceEndSession

    sent_messages = []
    ws_client.add_middleware("all", lambda msg, _: sent_messages.append(msg))
    ws_client.add_middleware(client_message_type, session_ender)

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    assert len(mock_server.messages_received) == expect_received_count
    assert len(sent_messages) == expect_sent_count


def test_update_transcription_config_sends_set_recognition_config(mock_server):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    def config_updater(msg):  # pylint: disable=unused-argument
        new_config = copy.deepcopy(transcription_config)
        new_config.language = "ja"
        ws_client.update_transcription_config(new_config)

    ws_client.add_event_handler(ServerMessageType.RecognitionStarted, config_updater)

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    set_recognition_config_msgs = mock_server.find_messages_by_type(
        "SetRecognitionConfig"
    )
    assert len(set_recognition_config_msgs) == 1
    assert (
        set_recognition_config_msgs[0]["transcription_config"]["language"] == "ja"
    )  # noqa


def test_start_recognition_sends_speaker_diarization_config(mock_server):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )
    transcription_config.speaker_diarization_config = RTSpeakerDiarizationConfig(
        max_speakers=5
    )

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    start_recognition_msgs = mock_server.find_messages_by_type("StartRecognition")
    assert len(start_recognition_msgs) == 1
    assert (
        start_recognition_msgs[0]["transcription_config"]["speaker_diarization_config"][
            "max_speakers"
        ]
        == 5
    )  # noqa


def test_client_stops_when_asked_and_sends_end_of_stream(mock_server):
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )

    num_messages_before_stop = 0

    def stopper(msg):  # pylint: disable=unused-argument
        nonlocal num_messages_before_stop
        num_messages_before_stop = len(mock_server.messages_received)
        ws_client.stop()

    ws_client.add_event_handler(ServerMessageType.RecognitionStarted, stopper)

    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)
    mock_server.wait_for_clean_disconnects()

    num_messages_after_stop = len(mock_server.messages_received)
    assert num_messages_before_stop + 1 == num_messages_after_stop
    assert mock_server.messages_received[-1]["message"] == "EndOfStream"


def test_helpful_error_message_received_on_connection_reset_error():
    """Tests that if connection to the server fails with
    a ConnectionResetError then a helpful error message is logged.
    """
    ws_client, _, _ = default_ws_client_setup("wss://this-url-wont-be-used:1")

    @contextlib.asynccontextmanager
    async def mock_connect(*_, **__):
        raise ConnectionResetError("foo")
        # We need a yield here for this to be a valid context manager,
        # even though the code is unreachable. Without it we get an error
        # about a missing __anext__ attribute.
        yield None  # pylint: disable=unreachable

    mock_logger_error_method = MagicMock()

    with patch("websockets.connect", mock_connect):
        with patch.object(client.LOGGER, "error", mock_logger_error_method):
            try:
                ws_client.run_synchronously(
                    MagicMock(), TranscriptionConfig(language="en"), MagicMock()
                )
            except ConnectionResetError as exc:
                assert exc is not None


def test_extra_headers_are_passed_to_websocket_connect_correctly(mock_server):
    """Tests extra headers are passed correclty to the websocket onConnect call."""
    extra_headers = {"keyy": "value"}

    def call_exit(*args, **kwargs):
        raise Exception()

    connect_mock = MagicMock(side_effect=call_exit)
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )
    stream = MagicMock()
    with patch("websockets.connect", connect_mock):
        try:
            ws_client.run_synchronously(
                stream,
                transcription_config,
                audio_settings,
                extra_headers=extra_headers,
            )
        except Exception:
            assert len(connect_mock.mock_calls) == 1
            assert (
                connect_mock.mock_calls[0][2]["extra_headers"] == extra_headers
            ), f"Extra headers don't appear in the call list = {connect_mock.mock_calls}"


@pytest.mark.asyncio
async def test__buffer_semaphore():
    """Test the WebsocketClient internal BoundedSemaphore."""
    # pylint: disable=protected-access
    buffer_size = 123
    ws_client = client.WebsocketClient(
        ConnectionSettings(url="fake url", message_buffer_size=buffer_size)
    )
    await ws_client._init_synchronization_primitives()

    async def ensure_release_raises():
        with pytest.raises(ValueError) as ctx:
            await ws_client._buffer_semaphore.release()
        assert "BoundedSemaphore released too many times" in str(ctx.value)

    # The difference between a Semaphore and a BoundedSemaphore is that
    # with the latter, a ValueError is raised if you call release()
    # to increase the internal counter value above its initial value.
    await ensure_release_raises()

    async def acquire_x_times(times):
        for _ in range(times):
            await ws_client._buffer_semaphore.acquire()

    await acquire_x_times(buffer_size)

    for _ in range(buffer_size):
        ws_client._buffer_semaphore.release()

    await ensure_release_raises()

    await acquire_x_times(buffer_size - 1)
    assert not ws_client._buffer_semaphore.locked()

    await acquire_x_times(1)
    assert ws_client._buffer_semaphore.locked()

    task = asyncio.create_task(acquire_x_times(1))

    # task should timeout because it's 'stuck' waiting for the
    # semaphore to be released.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(task, timeout=0.5)

    assert ws_client._buffer_semaphore.locked()
    ws_client._buffer_semaphore.release()
    assert not ws_client._buffer_semaphore.locked()


@pytest.mark.asyncio
async def test__producer_happy_path(mocker):
    """
    Happy path _producer test where the client sends 8 audio chunks
    and then stops.
    """
    # pylint: disable=protected-access,too-many-locals
    no_chunks_to_send = 8
    buffer_size = no_chunks_to_send + 1
    ws_client = client.WebsocketClient(
        ConnectionSettings(url="fake url", message_buffer_size=buffer_size)
    )
    await ws_client._init_synchronization_primitives()
    original_state = deepcopy_state(ws_client)

    async_iter_mock = asynctest.MagicMock()
    async_iter_mock.return_value.__aiter__.return_value = range(no_chunks_to_send)
    mock_read_in_chunks = mocker.patch(
        "speechmatics.client.read_in_chunks", new=async_iter_mock
    )

    msgs_states = []
    async for msg in ws_client._producer("mock", 123):
        msgs_states.append((msg, deepcopy_state(ws_client)))
        assert not ws_client._buffer_semaphore.locked()
    mock_read_in_chunks.assert_called_once_with("mock", 123)

    exp_iters = no_chunks_to_send + 1
    exp_final_seq_no = no_chunks_to_send
    exp_current_seq_no = 0
    for index, value in enumerate(msgs_states):
        msg, state = value

        if index < exp_iters - 1:
            assert msg == index  # from range in mock_read_in_chunks
            exp_current_seq_no += 1
            cmp_dicts(original_state, state, exp_diffs={"seq_no": exp_current_seq_no})
        else:
            assert msg == json.dumps(
                {"message": "EndOfStream", "last_seq_no": exp_final_seq_no}
            )
            cmp_dicts(original_state, state, exp_diffs={"seq_no": exp_final_seq_no})

    assert exp_iters == len(msgs_states)

    cmp_dicts(
        original_state,
        deepcopy_state(ws_client),
        exp_diffs={"seq_no": exp_final_seq_no},
    )


@pytest.mark.asyncio
async def test__producer_semaphore_pause_and_resume(mocker):
    """
    Test simulating the client sending audio chunks to a server faster
    than it can reply to them with AudioAdded acks causing the client
    throttling logic to kick-in.
    """
    # pylint: disable=protected-access,too-many-locals
    no_chunks_to_send = 5
    buffer_size = no_chunks_to_send - 1
    exp_iters = no_chunks_to_send + 1
    ws_client = client.WebsocketClient(
        ConnectionSettings(url="fake url", message_buffer_size=buffer_size)
    )
    await ws_client._init_synchronization_primitives()

    async_iter_mock = asynctest.MagicMock()
    async_iter_mock.return_value.__aiter__.return_value = range(no_chunks_to_send)
    mocker.patch(
        "speechmatics.client.read_in_chunks", new=async_iter_mock
    )  # pylint: disable=unused-variable

    msgs = []

    async def iter_through__producer():
        async for msg in ws_client._producer("mock", 123):
            msgs.append(msg)

    async def release_semaphore():  # acting as the slow server
        times_when_buffer_full = 0
        while True:
            if len(msgs) == buffer_size:
                times_when_buffer_full += 1
            if times_when_buffer_full > 5 and ws_client._buffer_semaphore.locked():
                ws_client._buffer_semaphore.release()
                break
            await asyncio.sleep(0.0001)

    task1 = asyncio.create_task(iter_through__producer())
    task2 = asyncio.create_task(release_semaphore())

    done, pending = await asyncio.wait(
        [task1, task2], return_when=asyncio.FIRST_EXCEPTION, timeout=5
    )
    assert len(done) == 2
    assert not pending

    for task in done:
        assert not task.exception()

    assert len(msgs) == exp_iters


@pytest.mark.asyncio
async def test__producer_semaphore_timeout(mocker):
    """
    Test simulating the client continually sending audio chunks to
    a server that isn't responding with AudioAdded acks."""
    # pylint: disable=protected-access,too-many-locals
    no_chunks_to_send = 5
    buffer_size = no_chunks_to_send - 1
    quick_timeout = 0.1
    ws_client = client.WebsocketClient(
        ConnectionSettings(
            url="fake url",
            message_buffer_size=buffer_size,
            semaphore_timeout_seconds=quick_timeout,
        )
    )
    await ws_client._init_synchronization_primitives()

    async_iter_mock = asynctest.MagicMock()
    async_iter_mock.return_value.__aiter__.return_value = range(no_chunks_to_send)
    mocker.patch(
        "speechmatics.client.read_in_chunks", new=async_iter_mock
    )  # pylint: disable=unused-variable

    msgs = []

    async def ensure_timeout():
        async for msg in ws_client._producer("mock", 123):
            msgs.append(msg)

    async def ensure_timeout_happens_in_time():
        await asyncio.sleep(quick_timeout + 1)
        raise AssertionError("we should of timed-out by now")

    task1 = asyncio.create_task(ensure_timeout())
    task2 = asyncio.create_task(ensure_timeout_happens_in_time())

    done, pending = await asyncio.wait(
        [task1, task2], return_when=asyncio.FIRST_EXCEPTION, timeout=None
    )
    assert len(done) == 1
    assert len(pending) == 1

    done_task = done.pop()
    assert ".ensure_timeout()" in str(done_task)
    assert isinstance(done_task.exception(), asyncio.TimeoutError)

    pending_task = pending.pop()
    assert ".ensure_timeout_happens_in_time()" in str(pending_task)
    pending_task.cancel()

    assert len(msgs) == buffer_size


def test_language_pack_info_is_stored(mock_server):
    """
    Tests that `language_pack_info` from the `RecognitionStarted` message is stored by the client.
    """
    ws_client, transcription_config, audio_settings = default_ws_client_setup(
        mock_server.url
    )
    with open(path_to_test_resource("ch.wav"), "rb") as audio_stream:
        ws_client.run_synchronously(audio_stream, transcription_config, audio_settings)

    info = ws_client.get_language_pack_info()
    assert info is not None
    assert info["language_code"] == "en"


def test_batch_mock_jobs(httpx_mock: HTTPXMock):
    # submit job
    httpx_mock.add_response(content=b'{"id":"p8t3dcrign"}')

    # check job status
    with open(path_to_test_resource("batch-job-status.json"), "rb") as file:
        job_status = file.read()
    httpx_mock.add_response(content=job_status)

    # get job result
    with open(path_to_test_resource("batch-job-transcript.json"), "rb") as file:
        transcript = file.read()
    httpx_mock.add_response(content=transcript)

    settings = ConnectionSettings(
        url="https://speechmatics.com/foo/v2",
        auth_token="bar",
    )

    conf = BatchTranscriptionConfig(
        language="en",
    )

    with BatchClient(settings) as batch_client:
        job_id = batch_client.submit_job(
            audio=("foo", b"some audio data"),
            transcription_config=conf,
        )

        actual_transcript = batch_client.wait_for_completion(
            job_id, transcription_format="txt"
        )
        assert transcript.decode("utf-8") == actual_transcript


def test_client_apikey_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "realtime_url": "http://rt-example.com",
        },
    )
    sm_client = client.WebsocketClient("fake_api_key")
    assert "fake_api_key" == sm_client.connection_settings.auth_token
    assert "http://rt-example.com" == sm_client.connection_settings.url
    assert sm_client.connection_settings.generate_temp_token


def test_client_empty_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "realtime_url": "http://rt-example.com",
            "auth_token": "home_token",
            "generate_temp_token": True,
        },
    )
    sm_client = client.WebsocketClient()
    assert "http://rt-example.com" == sm_client.connection_settings.url
    assert "home_token" == sm_client.connection_settings.auth_token
    assert sm_client.connection_settings.generate_temp_token


def test_client_url_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "auth_token": "home_token",
        },
    )
    sm_client = client.WebsocketClient(ConnectionSettings("http://rt-example.com"))
    assert "home_token" == sm_client.connection_settings.auth_token


def test_batch_client_empty_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "batch_url": "http://batch-example.com/v2",
            "auth_token": "home_token",
            "generate_temp_token": True,
        },
    )
    with BatchClient() as batch_client:
        assert "http://batch-example.com/v2" == batch_client.connection_settings.url
        assert "home_token" == batch_client.connection_settings.auth_token
        assert batch_client.connection_settings.generate_temp_token


def test_batch_client_url_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "auth_token": "home_token",
        },
    )
    with BatchClient() as batch_client:
        assert "home_token" == batch_client.connection_settings.auth_token


def test_batch_client_api_key_constructor(mocker):
    mocker.patch(
        "speechmatics.models.read_config_from_home",
        return_value={
            "batch_url": "http://batch-example.com/v2",
        },
    )
    with BatchClient("home_token") as batch_client:
        assert "http://batch-example.com/v2" == batch_client.connection_settings.url
        assert "home_token" == batch_client.connection_settings.auth_token
        assert batch_client.connection_settings.generate_temp_token


def deepcopy_state(obj):
    """
    Return a deepcopy of the __dict__ (or state) of an object but ignore
    the keys that cause trouble when trying to copy.deepcopy them.
    """
    state = vars(obj)
    state_copy = {}

    # copy.deepcopy will raise an exception on these types because they
    # can't be pickled.
    # The try..except method you'd expect to see here causes pytest warnings
    # when run with the -s flag so we explicitly name the types
    # to skip instead.
    types_to_ignore = (ConnectionSettings, asyncio.Event, asyncio.Semaphore)

    for key in state:
        if not isinstance(state[key], types_to_ignore):
            state_copy[key] = copy.deepcopy(state[key])

    return state_copy


def cmp_dicts(before_dict, after_dict, exp_diffs=None):
    if exp_diffs:
        before_dict = copy.deepcopy(before_dict)
        after_dict = copy.deepcopy(after_dict)
        for exp_diff_key, exp_diff_value in exp_diffs.items():
            assert exp_diff_key in before_dict
            assert exp_diff_key in after_dict
            before_value = before_dict.pop(exp_diff_key)
            after_value = after_dict.pop(exp_diff_key)
            assert before_value != after_value
            assert exp_diff_value == after_value
    assert before_dict == after_dict
