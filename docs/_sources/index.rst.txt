.. speechmatics-python documentation master file, created by
   sphinx-quickstart on Wed Dec  4 12:51:49 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

speechmatics-python
===================

speechmatics-python provides API wrapper and CLI to access the Speechmatics Realtime and Batch API v2.


Example library usage
---------------------

The example below illustrates a waveform audio file being opened and transcribed with Realtime. ::

    import speechmatics

    LANGUAGE = "en"
    AUDIO_FILE_PATH = "/path/to/file"
    CONNECTION_URL = f"wss://eu2.rt.speechmatics.com/v2/{LANGUAGE}"
    AUTH_TOKEN = "add token here"

    # Create a transcription client
    ws = speechmatics.client.WebsocketClient(
        speechmatics.models.ConnectionSettings(
            url=CONNECTION_URL,
            auth_token=AUTH_TOKEN,
            generate_temp_token=True, # Enterprise customers don't need to provide this parameter
        )
    )


    # Define an event handler to print the partial transcript
    def print_partial_transcript(msg):
        print(f"(PART) {msg['metadata']['transcript']}")


    # Define an event handler to print the full transcript
    def print_transcript(msg):
        print(f"(FULL) {msg['metadata']['transcript']}")


    # Register the event handler for partial transcript
    ws.add_event_handler(
        event_name=speechmatics.models.ServerMessageType.AddPartialTranscript,
        event_handler=print_partial_transcript,
    )

    # Register the event handler for full transcript
    ws.add_event_handler(
        event_name=speechmatics.models.ServerMessageType.AddTranscript,
        event_handler=print_transcript,
    )

    settings = speechmatics.models.AudioSettings()

    # Define transcription parameters
    conf = speechmatics.models.TranscriptionConfig(
        language=LANGUAGE,
        enable_partials=True,
    )

    with open("example.wav", 'rb') as file:
        ws.run_synchronously(file, conf, settings)


Command-line usage
------------------

Please see the
`GitHub readme <https://github.com/speechmatics/speechmatics-python/blob/master/README.md#example-command-line-usage>`_.


Reference
---------

.. toctree::
   :maxdepth: 2

   client
   batch_client
   exceptions
   helpers
   models


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
