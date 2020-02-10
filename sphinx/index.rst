.. speechmatics-python documentation master file, created by
   sphinx-quickstart on Wed Dec  4 12:51:49 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

speechmatics-python
===================

speechmatics-python provides API wrapper and CLI to access the Speechmatics Realtime API v2.


Example library usage
---------------------

The example below illustrates a waveform audio file being opened and transcribed. ::

    import speechmatics

    # Define connection parameters
    conn = speechmatics.models.ConnectionSettings(
        url="ws://localhost:9000/v2",
        ssl_context=None,
    )

    # Create a transcription client
    ws = speechmatics.client.WebsocketClient(conn)

    # Define transcription parameters
    conf = speechmatics.models.TranscriptionConfig(
        language='en',
    )

    # Define an event handler to print the transcript
    def print_transcript(msg):
        print(msg['metadata']['transcript'])

    # Register the event handler
    ws.add_event_handler(
        event_name=speechmatics.models.ServerMessageType.AddTranscript,
        event_handler=print_transcript,
    )

    # Open the audio file
    f = open('sample.wav', 'rb')

    # Initiate transcription
    ws.run_synchronously(f, conf, speechmatics.models.Audio())


Command-line usage
------------------

Please see the
`GitHub readme <https://github.com/speechmatics/speechmatics-python/blob/master/README.md#example-command-line-usage>`_.


Reference
---------

.. toctree::
   :maxdepth: 2

   client
   exceptions
   helpers
   models


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
