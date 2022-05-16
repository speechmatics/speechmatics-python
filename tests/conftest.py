import ssl
import threading
import asyncio
import time
import functools

import websockets
import pytest

from .mock_rt_server import MockRealtimeLogbook, mock_server_handler
from .utils import path_to_test_resource


def server_ssl_context():
    """
    Returns an SSL context for the mock RT server to use, with a self signed
    certificate.
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(
        path_to_test_resource("dummy_cert"),
        keyfile=path_to_test_resource("dummy_key"),
        password=lambda: "rohho3Uf",
    )
    return ssl_context


@pytest.fixture()
def mock_server(unused_tcp_port):
    """
    Fixture for creating a mock RT server. The server is designed
    to behave very similarly to the actual RT server, but returns
    dummy responses to most messages.

    The server runs in a background thread and is cleaned up as part of the
    fixture's tear-down step.

    Yields:
        tests.mock_rt_server.MockRealtimeLogbook: An object used to record
        information about the messages received and sent by the mock server.
    """
    port = unused_tcp_port
    logbook = MockRealtimeLogbook()
    logbook.url = f"wss://127.0.0.1:{port}/v2"
    mock_server_handler_with_logbook = functools.partial(
        mock_server_handler, logbook=logbook
    )

    async def server_thread(handler):
        try:
            async with websockets.serve(  # pylint: disable=no-member
                handler, host="127.0.0.1", port=port, ssl=server_ssl_context()
            ) as logbook.server:
                await asyncio.Future()
        except asyncio.CancelledError:
            asyncio.get_event_loop().stop()

    # Start extra event loop and start a mock server
    event_loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=event_loop.run_forever)
    server_thread_future = asyncio.run_coroutine_threadsafe(
        server_thread(mock_server_handler_with_logbook), event_loop
    )
    loop_thread.start()
    # Wait until the thread is ready.
    time.sleep(0.5)

    yield logbook

    # Kill the server gracefully.
    server_thread_future.cancel()
    loop_thread.join()
