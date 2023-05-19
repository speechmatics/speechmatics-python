This example shows how you can use Speechmatics to transcribe an online video (for example from youtube).
Transcribed content is printed to stdout. You can also choose to display a translation of the transcription, by specifying `--translation-languages`.

## Requirements
We assume you have speechmatics-python and its dependencies installed. To run this example you additionally need to install the package streamlink.
```bash
pip3 install streamlink
```

## Running the example
The only required input is the url of the video you'd like to transcribe. The auth token will be the one set in your Speechmatics [config](https://gitlab1.speechmatics.io/python/speechmatics-python-internal/-/tree/master/#configuring-auth-tokens).
```bash
python3 -m youtube_transcribe --input-url https://youtu.be/x438-2c59l8
```
### Additional parameters

A subset of the speechmatics cli options can be specified, check the docs to see what other options can be added.

* `--output-dir`: specify a directory in which which to save the transcription/translation in json and text formats.
* `--lang`: language of the video. 
* `--translation-langs`: comma separated list of languages to translate the content into.
* `--max-delay`: Maximum acceptable delay before sending a piece of transcript.
* `--enable-partials`: Whether to return partials for both transcripts and translation.

## Alternative method
Also using streamlink, you can pipe the sound from a youtube video into the main speechmatics cli tool.
```bash
streamlink "https://www.youtube.com/watch?v=9Auq9mYxFEE" best --loglevel none --output - |\
ffmpeg -loglevel quiet -i pipe: -vn -f wav - |\
speechmatics rt transcribe -
```