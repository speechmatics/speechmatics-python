This is an example showing how Speechmatics transcription can be used to transcribe video and audio streams in Real-Time.
For instance, with this we could transcribe a SRT stream once and distribute it to many clients.

This is implemented using WebSocket.
Clients connect to the `transcript_distribution_server` and access a URL to be transcribed.
Internally the `transcript_distribution_server` creates a Speechmatics Real-Time transcription session for each URL,
and forwards the text to all connected clients.

## Install requirements (macOS)

```bash
brew install ffmpeg
pip3 install -r requirements.txt

# For testing
brew install websocat
```

## Running

Start the server with

```bash
python3 transcript_distribution_server.py --port 8765
```

Connect with your client to e.g. `ws://localhost:8765`,
with https://github.com/vi/websocat this can be done with:
```bash
websocat ws://127.0.0.1:8765
```
> {"message": "Initialised", "info": "Waiting for message specifing desired stream url"}

The server expects an initial JSON message to start streaming:
```json
{"url": "https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd", "language": "en"}
```

Now the client will receive messages in JSON format until the stream ends or the client disconnects.
