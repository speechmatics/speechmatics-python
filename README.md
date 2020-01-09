# speechmatics-python &ensp; [![Build Status](https://travis-ci.org/speechmatics/speechmatics-python.svg?branch=master)](https://travis-ci.org/speechmatics/speechmatics-python) [![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/speechmatics/speechmatics-python/blob/master/LICENSE.txt) [![codecov](https://codecov.io/gh/speechmatics/speechmatics-python/branch/master/graph/badge.svg)](https://codecov.io/gh/speechmatics/speechmatics-python)

<a href="https://www.speechmatics.com/"><img src="https://speechmatics.github.io/speechmatics-python/_static/logo.png" width="25%" align="left"></a>

**speechmatics-python** provides a reference client for interfacing with version 2 of the Speechmatics Realtime ASR API. A command line interface is also provided for convenience.

## Getting started

- Make sure that you are running Python 3.7 or greater and install the dependencies

   ```shell
   $ python3 --version
   $ pip install git+https://github.com/speechmatics/speechmatics-python
   ```

- View the help message to make sure everything has been installed and setup

   ```shell
   $ speechmatics --help
   usage: speechmatics [-h] [-v] {transcribe} ...

   CLI for Speechmatics products.

   optional arguments:
     -h, --help    show this help message and exit
     -v            Set the log level for verbose logs. The number of flags
                   indicate the level, eg. -v is INFO and -vv is DEBUG.

   Commands:
     {transcribe}
       transcribe  Transcribe one or more audio file(s)
   ```

## Example usage

- A normal real time session using a .wav file as the input audio

   ```shell
   $ URL=ws://realtimeappliance.mycompany.io:9000/v2
   $ speechmatics transcribe--url $URL --lang en --ssl-mode=none example_audio.wav
   ```

- A normal real time session with a locally running container

   ```shell
   $ URL=ws://127.0.0.1:9000/v2
   $ speechmatics transcribe --url $URL --lang en --ssl-mode=none example_audio.wav
   ```

- Show the messages that are going over the websocket connection

   ```shell
   $ URL=ws://realtimeappliance.mycompany.io:9000/v2
   $ speechmatics transcribe -v --url $URL --lang en --ssl-mode=none example_audio.wav
   ```

- Similar to the first example, but this time the input audio is piped in

   ```shell
   $ URL=ws://realtimeappliance.mycompany.io:9000/v2
   $ cat example_audio.wav | speechmatics transcribe --ssl-mode=none --url $URL --lang en -
   ```

- The CLI also accepts an audio stream on standard input, meaning that you can stream in a live microphone feed for example.

   **MacOS example with ffmpeg**

   The command to list input devices available to ffmpeg is:

   ```shell
   $ ffmpeg -f avfoundation -list_devices true -i ""
   ```

   There needs to be at least one available microphone attached to your computer. The below command below gets the microphone output from ffmpeg and pipes it into the speechmatics client side
   library. You may need to change the sample rate to match the sample rate that your machine records at.
   You may need to replace `":default"` with something like `":0"` or `":1"` if you want to use a specific microphone.

   ```shell
   $ URL=ws://realtimeappliance.mycompanyio:9000/v2
   $ ffmpeg -loglevel quiet -f avfoundation -i ":default" -f f32le -c:a pcm_f32le - | speechmatics transcribe --ssl-mode=none --url $URL --raw pcm_f32le --sample-rate 44100 --lang en -
   ```


## Documentation

See the API Reference for the latest release at https://speechmatics.github.io/speechmatics-python/.

## Testing

To install development dependencies and run tests

    ```shell
    $ pip install -r requirements-dev.txt
    $ make test
    ```

## Support

If you have any issues with this library or encounter any bugs then please get in touch with us at support@speechmatics.com.

---

License: [MIT](LICENSE.txt)
