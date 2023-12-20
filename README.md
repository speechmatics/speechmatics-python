# speechmatics-python &ensp; ![Tests](https://github.com/speechmatics/speechmatics-python/workflows/Tests/badge.svg) [![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/speechmatics/speechmatics-python/blob/master/LICENSE.txt) ![PythonSupport](https://img.shields.io/badge/Python-3.7%2B-green)

Python client library and CLI for Speechmatics Realtime and Batch ASR v2 APIs.


## Getting started

To install from PyPI:
```bash
pip install speechmatics-python
```
To install from source:
```bash
git clone https://github.com/speechmatics/speechmatics-python
cd speechmatics-python && python setup.py install
```
Windows users may need to run the install command with an extra flag:
```bash
python setup.py install --user
```

## Docs

The speechmatics python SDK and CLI is documented at https://speechmatics.github.io/speechmatics-python/.

The Speechmatics API and product documentation can be found at https://docs.speechmatics.com.

## Real-Time Client Usage
```python
from speechmatics.models import *
import speechmatics

# Change to your own file
PATH_TO_FILE = "tests/data/ch.wav"
LANGUAGE = "en"

# Generate an API key at https://portal.speechmatics.com/manage-access/
API_KEY = ""

# Create a transcription client from config defaults
sm_client = speechmatics.client.WebsocketClient(API_KEY)

sm_client.add_event_handler(
    event_name=ServerMessageType.AddPartialTranscript,
    event_handler=print,
)

sm_client.add_event_handler(
    event_name=ServerMessageType.AddTranscript,
    event_handler=print,
)

conf = TranscriptionConfig(
    language=LANGUAGE, enable_partials=True, max_delay=5, enable_entities=True,
)

print("Starting transcription (type Ctrl-C to stop):")
with open(PATH_TO_FILE, "rb") as fd:
    try:
        sm_client.run_synchronously(fd, conf)
    except KeyboardInterrupt:
        print("\nTranscription stopped.")

```

## Batch Client Usage
```python
from speechmatics.models import ConnectionSettings, BatchTranscriptionConfig
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError

API_KEY = "YOUR_API_KEY"
PATH_TO_FILE = "example.wav"
LANGUAGE = "en"

# Open the client using a context manager
with BatchClient(API_KEY) as client:
    try:
        job_id = client.submit_job(PATH_TO_FILE, BatchTranscriptionConfig(LANGUAGE))
        print(f'job {job_id} submitted successfully, waiting for transcript')

        # Note that in production, you should set up notifications instead of polling.
        # Notifications are described here: https://docs.speechmatics.com/features-other/notifications
        transcript = client.wait_for_completion(job_id, transcription_format='txt')
        # To see the full output, try setting transcription_format='json-v2'.
        print(transcript)
    except HTTPStatusError as e:
        if e.response.status_code == 401:
            print('Invalid API key - Check your API_KEY at the top of the code!')
        elif e.response.status_code == 400:
            print(e.response.json()['detail'])
        else:
            raise e
```

## Example command-line usage

A complete list of commands and flags can be found in the SDK docs at https://speechmatics.github.io/speechmatics-python/.

  ### Configuring Auth Tokens
- Setting an auth token for CLI authentication:
   ```bash
   speechmatics config set --auth-token $AUTH_TOKEN
   ```
  Auth tokens are stored in toml config at HOME_DIR/.speechmatics/config.
  You may also set the auth_token for each CLI command using the --auth-token flag.
  The --auth-token flag overrides the value stored in the config file, e.g.
   ```bash
   speechmatics transcribe --auth-token $AUTH_TOKEN example_audio.wav
   ```

- Removing an auth_token from the toml file:
   ```bash
   speechmatics config unset --auth-token
   ```

- Setting URLs for connecting to transcribers. These values can be used in places of the --url flag:
   ```bash
   speechmatics config set --rt-url wss://eu2.rt.speechmatics.com/v2 --batch-url https://asr.api.speechmatics.com/v2
   ```

- Unsetting transcriber URLs in the toml config:
   ```bash
   speechmatics config unset --rt-url --batch-url
   ```

- Setting URLs for connecting to transcribers. These values can be used in places of the --url flag:
   ```bash
   speechmatics config set --rt-url wss://eu2.rt.speechmatics.com/v2 --batch-url https://asr.api.speechmatics.com/v2
   ```

- Unsetting transcriber URLs in the toml config:
   ```bash
   speechmatics config unset --rt-url --batch-url
   ```

  ### Realtime ASR
- Starting a real-time session for self-service SaaS customers using a .wav file as the input audio:

   ```bash
   speechmatics transcribe --lang en example_audio.wav
   ```

- Real-time transcription of online stream (needs ffmpeg installed):
  ```bash
  ffmpeg -v 0 -i https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd \
  -f s16le -ar 44100 -ac 1 -acodec pcm_s16le - | \
  speechmatics transcribe --raw pcm_s16le --sample-rate 44100 -

- Starting a real-time session for enterprise SaaS customers using a .wav file as the input audio:

   ```bash
   # Point URL to the a SaaS enterprise runtime
   URL=wss://neu.rt.speechmatics.com/v2/en

   speechmatics transcribe --url $URL example_audio.wav
   ```

- Starting a real-time session for on-prem customers using a .wav file as the input audio:

   ```bash
   # Point URL to the local instance of the realtime appliance
   URL=ws://realtimeappliance.yourcompany:9000/v2

   speechmatics transcribe --url $URL --lang en --ssl-mode none example_audio.wav
   ```

- Show the messages that are going over the websocket connection using verbose output:

   ```bash
   speechmatics -v transcribe --url $URL --ssl-mode none example_audio.wav
   ```

- The CLI also accepts an audio stream on standard input.
  Transcribe the piped input audio:

   ```bash
   cat example_audio.wav | speechmatics transcribe --url $URL --ssl-mode none -
   ```

- Pipe audio directly from the microphone (example uses MacOS with [ffmpeg](https://ffmpeg.org/ffmpeg-devices.html#avfoundation))

  List available input devices:

  ```bash
  ffmpeg -f avfoundation -list_devices true -i ""
  ```

  There needs to be at least one available microphone attached to your computer.
  The command below gets the microphone input and pipes it to the transcriber.
  You may need to change the sample rate to match the sample rate that your machine records at.
  You may also need to replace `:default` with something like `:0` or `:1` if you want to use a specific microphone.

  ```bash
  ffmpeg -loglevel quiet -f avfoundation -i ":default" -f f32le -acodec pcm_f32le -ar 44100 - \
  >   | speechmatics transcribe --url $URL --ssl-mode none --raw pcm_f32le --sample-rate 44100 -
  ```

- Transcribe in real-time with partials (example uses Ubuntu with ALSA).
  In this mode, the transcription engine produces words instantly, which may get updated as additional context becomes available.

  List available input devices:

  ```bash
  cat /proc/asound/cards
  ```

  Record microphone audio and pipe to transcriber:

  ```bash
  ffmpeg -loglevel quiet -f alsa -i hw:0 -f f32le -acodec pcm_f32le -ar 44100 - \
      | speechmatics transcribe --url $URL --ssl-mode none --enable-partials --raw pcm_f32le --sample-rate 44100 -
  ```

  Add the `--print-json` argument to see the raw JSON transcript messages being sent rather than just the plaintext transcript.

  ### Batch ASR
- Submit a .wav file for batch ASR processing

   ```bash
   speechmatics batch transcribe --lang en example_audio.wav
   ```

- Files may be submitted for asynchronous processing

    ```bash
   speechmatics batch submit example_audio.wav
    ```

- Enterprise SaaS and on-prem customers can point to a custom runtime:

   ```bash
   # Point URL to a custom runtime (in this case, the trial runtime)
   URL=https://trial.asr.api.speechmatics.com/v2/

   speechmatics batch transcribe --url $URL example_audio.wav
   ```

- Check processing status of a job

    ```bash
   # $JOB_ID is from the submit command output
   speechmatics batch job-status --job-id $JOB_ID
    ```

- Retrieve completed transcription

    ```bash
   # $JOB_ID is from the submit command output
   speechmatics batch get-results --job-id $JOB_ID
    ```

- Submit a job with automatic language identification

    ```bash
   speechmatics batch transcribe --language auto --langid-langs en,es example_audio.wav
    ```
    If Speechmatics is not able to identify a language with high enough confidence,  the job will be rejected. This is to reduce the risk of transcribing incorrectly.

    `--langid-langs` is optional and specifies what language(s) you expect to be detected in the source files.


- Submit a job with translation

    ```bash
  speechmatics batch transcribe --translation-langs de,es --output-format json-v2 example_audio.wav
    ```
  `--translation-langs` is supported in asynchronous mode as well, and translation output can be retrieved using `get-results` with `--output-format json-v2` set.

  When combining language identification with translation, we can't know if the identified language can be translated
  to your translation targets. If the translation pair is not supported, the error will be recorded in the metadata of the transcript.

- Start a real-time transcription with translation session using microphone audio and pipe to transcriber

  ```bash
  ffmpeg -loglevel quiet -f alsa -i hw:0 -f f32le -acodec pcm_f32le -ar 44100 - \
      | speechmatics rt transcribe --url $URL --ssl-mode none --raw pcm_f32le --sample-rate 44100 \
  --print-json --translation-langs fr -
  ```

- Submit a job with summarization

  ```bash
  speechmatics batch transcribe --summarize --output-format json-v2 example_audio.wav
    ```

- Submit a job with sentiment analysis

  ```bash
  speechmatics batch transcribe --sentiment-analysis --output-format json-v2 example_audio.wav
    ```

- Submit a job with topic detection

  ```bash
  speechmatics batch transcribe --detect-topics --output-format json-v2 example_audio.wav
    ```

- Submit a job with auto chapters

  ```bash
  speechmatics batch transcribe --detect-chapters --output-format json-v2 example_audio.wav
    ```

  ### Custom Transcription Config File
- Instead of passing all the transcription options via the command line you can also pass a transcription config file.
  The config file is a JSON file that contains the transcription options.
  The config file can be passed to the CLI using the `--config-file` option.

    ```bash
  speechmatics transcribe --config-file transcription_config.json example_audio.wav
    ```
- The format of this JSON file is described in detail in the
  [Batch API documentation](https://docs.speechmatics.com/jobsapi#tag/TranscriptionConfig)
  and [RT API documentation](https://docs.speechmatics.com/rt-api-ref#transcription-config).


## SM Metrics

This package includes tooling for benchmarking transcription and diarization accuracy.

For more information, see the `asr_metrics/README.md`

## Testing

To install development dependencies and run tests

    pip install -r requirements-dev.txt
    make test


## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com.

---

License: [MIT](LICENSE.txt)
