# speechmatics-python &ensp; ![Tests](https://github.com/speechmatics/speechmatics-python/workflows/Tests/badge.svg) [![codecov](https://codecov.io/gh/speechmatics/speechmatics-python/branch/master/graph/badge.svg)](https://codecov.io/gh/speechmatics/speechmatics-python) [![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/speechmatics/speechmatics-python/blob/master/LICENSE.txt)

Python client library and CLI for Speechmatics Realtime and Batch ASR v2 APIs.


## Getting started

To install from PyPI:

    $ pip install speechmatics-python

To install from source:

    $ git clone https://github.com/speechmatics/speechmatics-python
    $ cd speechmatics-python && python setup.py install

Windows users may need to run the install command with an extra flag:

    $ python setup.py install --user

### Requirements

- Python 3.7+

## Docs

The speechmatics python SDK and CLI is documented at https://speechmatics.github.io/speechmatics-python/.

The Speechmatics API and product documentation can be found at https://docs.speechmatics.com.

## Example command-line usage

A complete list of commands and flags can be found in the SDK docs at https://speechmatics.github.io/speechmatics-python/.

  ### Configuring Auth Tokens
- Setting an auth token for CLI authentication:
   ```shell
   $ speechmatics config set --auth-token $AUTH_TOKEN
   ```
  Auth tokens are stored in toml config at HOME_DIR/.speechmatics/config.
  You may also set the auth_token for each CLI command using the --auth-token flag.
  The --auth-token flag overrides the value stored in the config file, e.g.
   ```shell
   $ speechmatics transcribe --auth-token $AUTH_TOKEN --generate-temp-token example_audio.wav
   ```

- Removing an auth_token from the toml file:
   ```shell
   $ speechmatics config unset --auth-token
   ```

- Setting --generate-temp-token flag globally for CLI authentication:
   ```shell
   $ speechmatics config set --generate-temp-token
   ```

- Unsetting generate temp token globally for CLI authentication:
   ```shell
   $ speechmatics config unset --generate-temp-token
   ```

  ### Realtime ASR
- Starting a real-time session for self-service SaaS customers using a .wav file as the input audio:

   ```shell
   $ speechmatics transcribe --lang en --generate-temp-token example_audio.wav
   ```

- Starting a real-time session for enterprise SaaS customers using a .wav file as the input audio:

   ```shell
   # Point URL to the a SaaS enterprise runtime
   $ URL=wss://neu.rt.speechmatics.com/v2/en

   $ speechmatics transcribe --url $URL example_audio.wav
   ```

- Starting a real-time session for on-prem customers using a .wav file as the input audio:

   ```shell
   # Point URL to the local instance of the realtime appliance
   $ URL=ws://realtimeappliance.yourcompany:9000/v2

   $ speechmatics transcribe --url $URL --lang en --ssl-mode none example_audio.wav
   ```

- Show the messages that are going over the websocket connection using verbose output:

   ```shell
   $ speechmatics -v transcribe --url $URL --ssl-mode none example_audio.wav
   ```

- The CLI also accepts an audio stream on standard input.
  Transcribe the piped input audio:

   ```shell
   $ cat example_audio.wav | speechmatics transcribe --url $URL --ssl-mode none -
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
  >   | speechmatics transcribe --url $URL --ssl-mode none --raw pcm_f32le --sample-rate 44100 -
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
      | speechmatics transcribe --url $URL --ssl-mode none --enable-partials --raw pcm_f32le --sample-rate 44100 -
  ```

  Add the `--print-json` argument to see the raw JSON transcript messages being sent rather than just the plaintext transcript.

  ### Batch ASR
- Submit a .wav file for batch ASR processing

   ```shell
   $ speechmatics batch transcribe --lang en example_audio.wav
   ```

- Files may be submitted for asynchronous processing

    ```shell
   $ speechmatics batch submit example_audio.wav
    ```

- Enterprise SaaS and on-prem customers can point to a custom runtime:

   ```shell
   # Point URL to a custom runtime (in this case, the trial runtime)
   $ URL=https://trial.asr.api.speechmatics.com/v2/

   $ speechmatics batch transcribe --url $URL example_audio.wav
   ```

- Check processing status of a job

    ```shell
   # $JOB_ID is from the submit command output
   $ speechmatics batch job-status --job-id $JOB_ID
    ```

- Retrieve completed transcription

    ```shell
   # $JOB_ID is from the submit command output
   $ speechmatics batch get-results --job-id $JOB_ID
    ```
  
  ### Custom Transcription Config File
- Instead of passing all the transcription options via the command line you can also pass a transcription config file.
  The config file is a JSON file that contains the transcription options.
  The config file can be passed to the CLI using the `--config-file` option.

    ```shell
  $ speechmatics transcribe --config-file transcription_config.json example_audio.wav
    ```
- The format of this JSON file is described in detail in the 
  [Batch API documentation](https://docs.speechmatics.com/jobsapi#tag/TranscriptionConfig)
  and [RT API documentation](https://docs.speechmatics.com/rt-api-ref#transcription-config).


## Testing

To install development dependencies and run tests

    $ pip install -r requirements-dev.txt
    $ make test


## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com.

---

License: [MIT](LICENSE.txt)
