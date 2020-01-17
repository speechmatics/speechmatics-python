import ssl
import threading

import pytest
from SimpleWebSocketServer import SimpleSSLWebSocketServer

from .mock_rt_server import MockRealtimeLogbook, MockRealtimeServer
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
def mock_server():
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
    logbook = MockRealtimeLogbook()
    logbook.url = "wss://127.0.0.1:8765/v2"
    MockRealtimeServer.logbook = logbook
    server = SimpleSSLWebSocketServer(
        "127.0.0.1", 8765, MockRealtimeServer, ssl_context=server_ssl_context()
    )
    server_should_stop = False

    def server_runner():
        while not server_should_stop:
            server.serveonce()

    thread = threading.Thread(name="server_runner", target=server_runner)
    thread.daemon = True
    thread.start()

    yield logbook

    server_should_stop = True
    thread.join(timeout=60.0)
    assert (
        not thread.is_alive()
    )  # check if the join timed out (this should never happen)
