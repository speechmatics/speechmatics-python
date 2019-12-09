import json
import logging
import time

from SimpleWebSocketServer import WebSocket


class MockRealtimeLogbook:
    """
    Contains information about what happened during an active session of the
    mock realtime server. This allows tests to make assertions about what
    should have happened, e.g. what messages should have been received.
    """

    def __init__(self):
        self.url = ""
        self.connection_request = None
        self.clients_connected_count = 0
        self.clients_disconnected_count = 0
        self.messages_received = []
        self.messages_sent = []

    def find_messages_by_type(self, msg_name):
        """
        Returns all messages received from the client of the given type.
        For `AddAudio` messages use `find_add_audio_messages`.

        Args:
            msg_name (str): The message type e.g. "SetRecognitionConfig"

        Returns:
            List[dict]: The matching list of messages.
        """
        return [
            msg
            for msg in self.messages_received
            if isinstance(msg, dict) and msg["message"] == msg_name
        ]

    def find_sent_messages_by_type(self, msg_name):
        """
        Returns all messages sent to the client of the given type.

        Args:
            msg_name (str): The message type e.g. "AddTranscript"

        Returns:
            List[dict]: The matching list of messages.
        """
        return [
            msg
            for msg in self.messages_sent
            if isinstance(msg, dict) and msg["message"] == msg_name
        ]

    def find_add_audio_messages(self):
        """
        Returns all binary `AddAudio` messages received from the client.

        Returns:
            List[bytearray]: The matching list of messages.
        """
        return [
            msg for msg in self.messages_received if not isinstance(msg, dict)]

    def find_start_recognition_message(self):
        """
        Returns the `StartRecognition` message received from the client,
        assuming it was sent.

        Raises:
            AssertionError: If `StartRecognition` was not received.

        Returns:
            dict: The `StartRecognition` message.
        """
        messages = self.find_messages_by_type("StartRecognition")
        assert len(messages) == 1
        return messages[0]

    def wait_for_clean_disconnects(self, num_disconnects=1, timeout=15):
        """
        Blocks until `clients_disconnected_count` is equal to the target value.
        This is a convenience for unit-tests which may need to wait until all
        connections have been closed cleanly.

        Args:
            num_disconnects (int, optional): Target number of disconnects to
                wait for.
            timeout (int, optional): Number of seconds to timeout after.

        Raises:
            TimeoutError: If we have been waiting longer than the given timeout
                value.
        """
        start = time.time()
        while True:
            if self.clients_disconnected_count >= num_disconnects:
                return
            if time.time() - start < timeout:
                time.sleep(0.2)
            else:
                raise TimeoutError(
                    "Timed out while waiting for client disconnects."
                )


class MockRealtimeServer(WebSocket):
    """
    A mock implementation of the Speechmatics Realtime ASR server,
    which returns dummy responses to most messages.
    """

    logbook = None

    def __init__(self, *args, **kwargs):
        self.next_audio_seq_no = 1
        super().__init__(*args, **kwargs)

    def handleMessage(self):
        """Deal with a message received from the client."""
        try:
            # This whole block is wrapped in a try/except because the default
            # behaviour of the SimpleWebSocketServer library is to silently
            # discard any exceptions raised by these handlers. This is very
            # unhelpful. A workaround is to catch and log any exceptions
            # explicitly here.
            logging.debug("%s %s", self.address, "incoming message")
            is_binary = not isinstance(self.data, str)
            if is_binary:
                message = self.data
            else:
                message = json.loads(self.data)

            self.logbook.messages_received.append(message)
            for response in self.get_responses(message, is_binary=is_binary):
                self.logbook.messages_sent.append(response)
                self.sendMessage(json.dumps(response).encode("utf-8"))
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception(str(exc))
            self.close(status=1011, reason="Internal server error")

    def handleConnected(self):
        """Called when a new client connects to the server."""
        logging.info("%s %s", self.address, "connected")
        self.logbook.connection_request = self.request
        self.logbook.clients_connected_count += 1

    def handleClose(self):
        """Called when a client disconnects from the server."""
        logging.info("%s %s", self.address, "closed")
        self.logbook.clients_disconnected_count += 1

    def get_responses(self, message, is_binary=False):
        """
        Optionally creates a response to the given message from the client.
        Either returns a dictionary with the response message or `None` if no
        response should be sent.

        Args:
            message (Union[dict, bytearray]): The message received from the
                client. Assumes that if the message is a standard JSON message
                it has already been parsed into a dictionary. AddAudio messages
                are expected to be binary bytearrays.
            is_binary (boolean, optional): Whether or not the message
                is binary, implying that the message is an AddAudio message.

        Raises:
            ValueError: If the message is invalid or has an unrecognized type.

        Returns:
            List[dict]: List of responses to the message.
        """
        responses = []
        if is_binary:
            # AddAudio is the only binary message, so we can assume it's that.
            responses.append(
                {"message": "AudioAdded", "seq_no": self.next_audio_seq_no}
            )
            self.next_audio_seq_no += 1

            # Answer immediately with a partial and a final.
            responses.append(dummy_add_partial_transcript())
            responses.append(dummy_add_transcript())
        else:
            msg_name = message.get("message")
            if not msg_name:
                raise ValueError(message)

            if msg_name == "StartRecognition":
                responses.append(
                    {
                        "message": "RecognitionStarted",
                        "id": "7c3003ae-fa23-45dc-a5cd-5b86bf56817b",
                    }
                )
            elif msg_name == "EndOfStream":
                responses.append({"message": "EndOfTranscript"})
            elif msg_name == "SetRecognitionConfig":
                pass
            else:
                raise ValueError("Unrecognized message: {}".format(message))

        return responses


def dummy_add_partial_transcript():
    """Returns a dummy AddPartialTranscript message."""
    return {
        "message": "AddPartialTranscript",
        "format": "2.1",
        "metadata": {"start_time": 0.0, "end_time": 1.0, "transcript": "foo"},
        "results": [
            {
                "type": "word",
                "start_time": 0.0,
                "end_time": 1.0,
                "alternatives": [
                    {"content": "foo", "confidence": 1.0, "language": "en"},
                ],
            },
        ],
    }


def dummy_add_transcript():
    """Returns a dummy AddTranscript message."""
    return {
        "message": "AddTranscript",
        "format": "2.1",
        "metadata": {
            "start_time": 0.0, "end_time": 2.0, "transcript": "Foo\nBar."},
        "results": [
            {
                "type": "word",
                "start_time": 0.0,
                "end_time": 1.0,
                "alternatives": [
                    {"content": "foo", "confidence": 1.0, "language": "en"},
                ],
            },
            {
                "type": "speaker_change",
                "start_time": 1.0,
                "end_time": 1.0,
                "score": 0.8,
            },
            {
                "type": "word",
                "start_time": 1.0,
                "end_time": 2.0,
                "alternatives": [
                    {"content": "bar", "confidence": 1.0, "language": "en"},
                ],
            },
            {
                "type": "punctuation",
                "start_time": 2.0,
                "end_time": 2.0,
                "alternatives": [{"content": ".", "confidence": 1.0}],
            },
        ],
    }
