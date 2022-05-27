import os
import ssl

from speechmatics.client import WebsocketClient
from speechmatics.models import AudioSettings, ConnectionSettings, TranscriptionConfig


def path_to_test_resource(file_name):
    """
    Given a file name in the test resources directory, returns a complete
    path to that file.

    Args:
        file_name (str): Name of the file in the test resources directory.

    Returns:
        str: Full path to the file relative to the current working directory.
    """
    path_here = os.path.dirname(os.path.abspath(__file__))
    resource_directory = os.path.join(path_here, "data/")
    file_path = os.path.join(resource_directory, file_name)
    return file_path


def default_ws_client_setup(mock_server_url):
    """
    Returns a 3-tuple with a WebsocketClient, TranscriptionConfig and
    AudioSettings all with default settings for use in test cases.

    Args:
        mock_server_url (str): address that the mock RT server is listening on.

    Returns:
        Tuple[WebsocketClient, TranscriptionConfig, AudioSettings]: Websocket
            client and other useful config objects.
    """

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn_settings = ConnectionSettings(url=mock_server_url, ssl_context=ssl_context)
    ws_client = WebsocketClient(conn_settings)

    transcription_config = TranscriptionConfig()
    audio_settings = AudioSettings()

    return ws_client, transcription_config, audio_settings
