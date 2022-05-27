# speechmatics-python &ensp; ![Tests](https://github.com/speechmatics/speechmatics-python/workflows/Tests/badge.svg) [![codecov](https://codecov.io/gh/speechmatics/speechmatics-python/branch/master/graph/badge.svg)](https://codecov.io/gh/speechmatics/speechmatics-python) [![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/speechmatics/speechmatics-python/blob/master/LICENSE.txt)

Python client library and CLI for Speechmatics Realtime and Batch ASR v2 APIs.


## Getting started

To install from PyPI:

    $ pip install speechmatics-python

To install from source:

    $ git clone https://github.com/speechmatics/speechmatics-python
    $ cd speechmatics-python && python setup.py install

### Requirements

- Python 3.7+

## Example command-line usage


### Realtime ASR
- A normal real time session using a .wav file as the input audio:

   ```shell
   # Point URL to the local instance of Speechmatics
   $ URL=ws://realtimeappliance.yourcompany:9000/v2

   $ speechmatics transcribe --url $URL --lang en --ssl-mode none example_audio.wav
   ```

- Show the messages that are going over the websocket connection:

   ```shell
   $ speechmatics -v transcribe --url $URL --lang en --ssl-mode none example_audio.wav
   ```

- The CLI also accepts an audio stream on standard input.
  Transcribe the piped input audio:

   ```shell
   $ cat example_audio.wav | speechmatics transcribe --ssl-mode none --url $URL --lang en -
   ```

- Pipe audio directly from the microphone (example uses MacOS with [ffmpeg](https://ffmpeg.org/ffmpeg-devices.html#avfoundation))

  List available input devices:

  ```shell
  $ ffmpeg -f avfoundation -list_devices true -i ""
  ```

  There needs to be at least one available microphone attached to your computer.
  The command below gets the microphone input and pipes it to the transcriber.
  You may need to change the sample rate to match the sample rate that your machine records at.
  You may also need to replace `:default` with something like `:0` or `:1` if you want to use a specific microphone.

  ```shell
  $ ffmpeg -loglevel quiet -f avfoundation -i ":default" -f f32le -acodec pcm_f32le -ar 44100 - \
  >   | speechmatics transcribe --ssl-mode none --url $URL --raw pcm_f32le --sample-rate 44100 --lang en -
  ```

- Transcribe in real-time with partials (example uses Ubuntu with ALSA).
  In this mode, the transcription engine produces words instantly, which may get updated as additional context becomes available.

  List available input devices:

  ```shell
  $ cat /proc/asound/cards
  ```

  Record microphone audio and pipe to transcriber:

  ```shell
  $ ffmpeg -loglevel quiet -f alsa -i hw:0 -f f32le -acodec pcm_f32le -ar 44100 - \
      | speechmatics transcribe --ssl-mode none --url $URL --enable-partials --raw pcm_f32le --sample-rate 44100 --lang en -
  ```

  ### Batch ASR
- Submit a .wav file for batch ASR processing

   ```shell
   # Point URL to Speechmatics SaaS (Batch Virtual Appliance is also supported)
   $ URL=https://asr.api.speechmatics.com/v2/
   $ AUTH_TOKEN='abcd01234'

   $ speechmatics batch transcribe --url $URL --auth-token $AUTH_TOKEN --lang en example_audio.wav
   ```

- Files may be submitted for asynchronous processing

    ```shell
   $ speechmatics batch submit --url $URL --auth-token $AUTH_TOKEN --lang en example_audio.wav
    ```

- Check processing status of a job

    ```shell
   # $JOB_ID is from the submit command output
   $ speechmatics batch job-status --url $URL --auth-token $AUTH_TOKEN --job-id $JOB_ID
    ```

- Retrieve completed transcription

    ```shell
   # $JOB_ID is from the submit command output
   $ speechmatics batch get-results --url $URL --auth-token $AUTH_TOKEN --job-id $JOB_ID
    ```


## API documentation

Please see https://speechmatics.github.io/speechmatics-python/.


## Testing

To install development dependencies and run tests

    $ pip install -r requirements-dev.txt
    $ make test


## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com.

---

License: [MIT](LICENSE.txt)
