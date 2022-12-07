# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [1.4.4] - 2022-12-06

### Added

- Check for error in submit job response

### Fixed

- Url ending in '/v2/' does not return 404 error anymore
- Perform non-blocking reads when reading chunks from a synchronous stream

## [1.4.3] - 2022-11-24

### Added

- Add --config-file CLI argument to allow passing a whole TranscriptionConfig JSON file to the transcriber

## [1.4.1] - 2022-10-28

### Updated

- Changed github workflow trigger to released

## [1.4.0] - 2022-10-27

### Added

- Add --generate-temp-token CLI argument to rt websocket setup to get temp token for rt authentication
- Add generate_temp_token optional boolean kwarg to connection settings, defaults to False
- Add new RT self-service runtime URL for eu2

## [1.3.0] - 2022-08-05

### Added
- Add --print-json CLI argument to enable printing transcripts as JSON rather than text
- Add `speechmatics.adapters` module with support for performing JSON to text conversion
- Add support for `language_pack_info` in the `RecognitionStarted` message

## [1.2.3] - 2022-07-22

### Fixed
- Restored postional `language` parameter to `TranscriptionConfig.__init__`

## [1.2.2] - 2022-07-20

### Added

- Support for enable entities, speaker diarization sensitivity, channel diarization labels in batch

### Changed

- Transformed <trascribe> command to follow the pattern of RT only for legacy compatibility
- Fix client crashing if 'url' parameter is omitted and now outputting informative message
- Changed diarization option <speaker_and_channel> to <channel_and_speaker_change> as that's what SaaS expects.
- Fix get-results to fetch the transcript
- Update batch delete job to return meaningful response

## [1.2.1] - 2022-06-17
- Update documentation for RT speaker diarization.

## [1.2.0] - 2022-06-14
- Add support for speaker diarization in RT, and support the max_speakers parameter

## [1.1.0] - 2022-06-13
- Remove support for --n_best_limit parameter

## [1.0.6] - 2022-06-01
- Remove unnecessary Version file use and updated documentation for batch_client

## [1.0.5] - 2022-05-26

- Added support for Batch ASR client

## [1.0.4] - 2022-05-19

- Add domain parameter

## [1.0.3] - 2022-04-22

- Fix an issue with an unhandled task exception when using run_synchronously with a timeout.

## [1.0.2] - 2022-04-14

- Remove default values from args parser for max-delay-mode and operating-point for 
  backwards compatibility with older versions of RTC.

## [1.0.1] - 2022-04-13

- Use later version of sphinx to generate docs (supports Python 3.10)
- Update Speechmatics logo
- Allow user to raise ForceEndSession from an event handler or middleware in order to
  forcefully end the transcription session early.

## [1.0.0] - 2022-03-23

- Publish to pypi.org not test.pypi.org.

## [0.0.19] - 2022-02-24

### Added

- Update helper text for enable-entities, max-delay, and max-delay-mode

## [0.0.18] - 2022-02-10

### Added

- Support for choosing mode of operation for max_delay via `max_delay_mode` in transcription config.

## [0.0.17] - 2022-01-19

### Added

- bump `websockets` dependency to 10.1 to get the fix for an issue it has with Python 3.10

## [0.0.16] - 2022-01-18

### Added

- bump `websockets` dependency to 9.1

## [0.0.15] - 2021-12-23

### Added

- Support for enabling inverse text normalization (ITN) entities via `enable_entities` in transcription config.


## [0.0.14] - 2021-09-07

### Added

- operating_point CLI option validation and documentation


## [0.0.13] - 2021-03-29

### Added

- operating_point CLI option and property in TranscriptionConfig


## [0.0.12] - 2021-02-10

### Fixed

- Fix seq_no persisting across sessions


## [0.0.11] - 2020-10-18

### Changed

- Migrate from Travis CI to GitHub Actions


## [0.0.10] - 2020-10-01

### Added

- Added authentication token support for RT-SaaS [@rakeshv247](https://github.com/rakeshv247).


[Unreleased]: https://github.com/speechmatics/speechmatics-python/compare/v0.0.11...HEAD
[0.0.11]: https://github.com/speechmatics/speechmatics-python/releases/tag/v0.0.11
[0.0.10]: https://github.com/speechmatics/speechmatics-python/releases/tag/v0.0.10
