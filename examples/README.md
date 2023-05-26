# Examples

This folder provides some examples of how the Speechmatics python client can be used to build different systems. The current examples include:

1. [notification_flow](./notification_flow/README.md) (webhooks)

An example implementation of how to use the Speechmatics notifications system (webhooks) to submit jobs for processing and receive alerts when the jobs are complete.

2. [transcribe_from_youtube](./transcribe_from_youtube/README.md)

Provide a URL to a YouTube video and receive a transcription in return. This is also capable of continuously transcribing streamed videos on YouTube.

3. [transcript_distribution_server](./transcript_distribution_server/README.md)

Demonstrates how to run a websocket server that acts as a proxy to a speechmatics transcriber. It allows multiple clients to connect to the same transcriber stream. This can be used, for example, for distributing a radio transcription stream to multiple clients based on a single audio source.

Each of the examples should have a separate README with all the necessary steps to get them up and running.