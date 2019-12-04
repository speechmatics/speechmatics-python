# speechmatics-py

This library provides a reference client for interfacing with version 2 of the Speechmatics Realtime ASR API.

A command line interface is also provided for convenience.

## Dependencies

The client depends on Python >= 3.7 since it makes use of some of the newer `asyncio` features introduced with Python 3.7.

Other requirements are listed under `requirements.txt`.

## Getting started

1. Make sure that you are running Python 3.7 or greater. The following will tell you what version of python you are running

   ```shell
   $ python3 --version
   Python 3.7.3
   ```

1. Install the python dependencies

   ```shell
   $ pip3 install -r requirements.txt
   Collecting websockets==8.0.2 (from -r requirements.txt (line 1))
     Downloading https://files.pythonhosted.org/packages/8b/6b/ dcbafe10a1b889f3d31bef7048dbfb23973d4b56e8fb47c9158c47fa5643/ websockets-8.0.2-cp37-cp37m-macosx_10_6_intel.whl (65kB)
       100% |████████████████████████████████| 71kB 4.1MB/s
   Installing collected packages: websockets
     Found existing installation: websockets 8.0
       Uninstalling websockets-8.0:
         Successfully uninstalled websockets-8.0
   Successfully installed websockets-8.0.2
   ```

1. View the help message to make sure everything has been installed and setup

   ```shell
   $ python3 -m speechmatics.cli --help
   usage: cli.py [-h] [-v] [--ssl-mode {regular,insecure,none}]
              [--buffer-size BUFFER_SIZE] [--debug] --url URL [--lang LANG]
              [--output-locale LOCALE]
              [--additional-vocab [ADDITIONAL_VOCAB [ADDITIONAL_VOCAB ...]]]
              [--additional-vocab-file VOCAB_FILEPATH] [--enable-partials]
              [--punctuation-permitted-marks PUNCTUATION_PERMITTED_MARKS]
              [--punctuation-sensitivity PUNCTUATION_SENSITIVITY]
              [--diarization {none,speaker_change}]
              [--speaker-change-sensitivity SPEAKER_CHANGE_SENSITIVITY]
              [--speaker-change-token] [--max-delay MAX_DELAY]
              [--raw ENCODING] [--sample-rate SAMPLE_RATE]
              [--chunk-size CHUNK_SIZE] [--n-best-limit N_BEST_LIMIT]
              FILEPATHS [FILEPATHS ...]

   ...
   ```

You are now ready to try out some examples, continue to the next section.

### Command Line examples

1. A normal real time session using a .wav file as the input audio

   ```shell
   $ URL=wss://realtimeappliance.mycompany.io:9000/v2
   $ python3 -m speechmatics.cli --url $URL --lang en --ssl-mode=insecure example_audio.wav
   ```

1. Show the messages that are going over the websocket connection

   ```shell
   $ URL=wss://realtimeappliance.mycompany.io:9000/v2
   $ python3 -m speechmatics.cli -v --url $URL --lang en --ssl-mode=insecure example_audio.wav
   ```

1. Similar to the first example, but this time the input audio is piped in

   ```shell
   $ URL=wss://realtimeappliance.mycompany.io:9000/v2
   $ cat example_audio.wav | python3 -m speechmatics.cli --ssl-mode=insecure --url $URL --lang en -
   ```

1. The CLI also accepts an audio stream on standard input, meaning that you can stream in a live microphone feed for example.
   This example requires `ffmpeg`. You may need to replace the `":0"` according to the numbering of your input devices.
   You may also need to change the sample rate to match your machine's recording sample rate.

   **Mac OS**

   ```shell
   $ URL=wss://realtimeappliance.mycompanyio:9000/v2
   $ ffmpeg -loglevel quiet -f avfoundation -i ":0" -f f32le -c:a pcm_f32le - | python3 -m speechmatics.cli --ssl-mode=insecure --url $URL --raw pcm_f32le --sample-rate 44100 --lang en -
   ```

## Testing

The unit tests for this project depend on `pytest` as well as any other packages listed in `requirements-test.txt`.
To run the unit tests:

```shell
pytest tests
```

## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com.

---

License: MIT
