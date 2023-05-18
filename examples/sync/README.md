# kitchen sync

This directory contains two example modules to help with batch conversion of
audio files:


## `sync`

* `sync.sync()` will transcribe a folder of audio files using the
  `BatchClient`, skipping files that you have already transcribed, and
  maintaining a database of results in `~/.config/speechmatics-sync`.
* `sync.search()` then provides an API for searching these transcripts.


## `kitchen`

The `kitchen` module provides a CLI wrapper around `sync`:

```
$ python3 -m examples.sync.kitchen $API_KEY mp3s/
5 unseen path(s) to checksum...
  checksuming good_morning.mp3
  checksuming financials.mp3
  checksuming music.mp3
  checksuming singing.mp3
  checksuming meeting1.mp3
5 unseen path(s) to transcribe...
...
```

You can then do searches on the command line:

```
> python3 -m examples.sync.kitchen $API_KEY mp3s/ --search earnings
00:39.0 mp3s/financials.mp3
  “...for details on this quarter's earnings, we now hand over to
  a man wearing a funny bowler hat...“
```
