# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.14.10] - 2024-06-21

## Fixed

- Disfluency option now exposed for batch.

## [1.14.9] - 2024-06-14

### Added
- Support for adding extra headers for RT websocket

## [1.14.8] - 2024-05-14

### Changed
- AudioEventsConfig class now defaults to empty dict instead of empty list when types not provided

## [1.14.7] - 2024-04-08

## Fixed

- Disfluency option is now backwards compatible.

## [1.14.6] - 2024-04-26

## Added

- Support for removing words tagged as disfluency.

## [1.14.5] - 2024-03-20

## Added

- Support for audio_events in Batch CLI.
- Support `types` whitelist for audio events.

## [1.14.4] - 2024-03-04

## Added

- Support for volume_threshold audio filtering in transcription config

## [1.14.3] - 2024-02-29

## Fixed

- Add audio_events_config to BatchTranscriptionConfig

## [1.14.2] - 2024-02-28

## Fixed

- Add audio_events_config to BatchConfig.to_config method

## [1.14.1] - 2024-02-21

## Fixed

- Proper flag handling for Audio Events

## [1.14.0] - 2024-02-12

### Added

- Support for the Audio Events feature

## [1.13.1] - 2023-12-21

### Changed
- Rename `metrics` to `asr_metrics`

### Fixed

- Fix import errors for asr_metrics module
- Misc fixes for asr_metrics module

## [1.13.0] - 2023-12-07

### Added

- Add metrics toolkit for transcription and diarization

## [1.12.0] - 2023-11-03

### Added

- Add support for batch auto chapters

## [1.11.1] - 2023-10-19

### Added

- Improve upload speeds for files submitted with the batch client
- Retry requests in batch client on httpx.ProtocolError

### Changed

- Remove generate-temp-token option from examples and examples in docs

## [1.11.0] - 2023-08-25

### Added

- Add support for batch topic detection

## [1.10.0] - 2023-08-02

### Added

- Add support for batch sentiment analysis
- Add support for transcribing multiple files at once (submit_jobs)

## [1.9.0] - 2023-06-07

### Fixed

- Fix error when language provided is whitespace

### Added

- Add support for transcript summarization
- Example of using notifications

## [1.8.3]

### Added

- Pass sdk information to batch and rt requests
- Add support for providing just auth_token ConnectionSettings
- Use default URLs + .toml config in python sdk

### Fixed

- Fixed an issue in the batch client where jobs with fetch_url were not able to be submitted
- Fixed reading translation config from config file

## [1.8.2]

### Fixed

- TranscriptionConfig.enable_partials defaults to False

## [1.8.1]

### Fixed

- setting TranscriptionConfig.enable_partials bool value to a string raises exception

### Added

- Support for batch and realtime urls in config .toml files

## [1.8.0]

### Added

- Added support for real-time translation
- Added `--enable-translation-partials` to enable partials for translation only
- Added `--enable-transcription-partials` to enable partials for transcription only

### Changed

- Updated `--enable-partials` to enable partials for both transcription and translation

### Added

- Add support for multiple profiles to the CLI tool

## [1.7.0] - 2023-03-01

### Added

- Add support for language identification

### Fixed

- Fixed an issue where `transcription_config` was not correctly loaded from the JSON config file
- CLI transcript output now properly handles UTF-8

## [1.6.4] - 2023-02-14

### Fixed

- printing finals in cli now correctly deletes partials for that segment

## [1.6.3] - 2023-02-14

### Fixed

- Type annotation for BatchSpeakerDiarizationConfig.speaker_sensitivity

## [1.6.2] - 2023-02-07

### Changed

- Always raise an exception on transcriber error

## [1.6.1] - 2023-02-02

### Changed

- Fix inconsistency in docs

## [1.6.0] - 2023-02-02

### Added

- Add support for translation

### Changed

- Raises ConnectionClosedException rather than returning when the websocket connection closes unexpectedly

## [1.5.1] - 2023-01-17

### Added

- Add sphinx-argparse to docs build pipeline to auto-document the CLI tool

### Changed

- Update the docs / help texts for the CLI tool

## [1.5.0] - 2023-01-13

### Added

- .toml config file support to set the auth token with CLI config set command
- CLI config unset command for removing properties from the toml file
- --generate-temp-token option to the set/unset config command and toml file
- Default URLs for self-service Batch and RT in the CLI

## [1.4.5] - 2023-01-03

### Added

- Documentation for base transcription config class `_TranscriptionConfig`
- Human-readable error outputs in the CLI

### Updated

- Improved error types in HTTP requests to capture errors more clearly
- Remove excess logging on errors and allow developer to catch errors
- Use environment variable SM_MANAGEMENT_PLATFORM_URL before defaulting to production MP API URL

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

[unreleased]: https://github.com/speechmatics/speechmatics-python/compare/v1.11.1...HEAD
[1.11.1]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.11.1
[1.11.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.11.0
[1.9.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.9.0
[1.8.3]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.8.3
[1.8.2]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.8.2
[1.8.1]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.8.1
[1.8.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.8.0
[1.7.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.7.0
[1.6.4]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.6.4
[1.6.3]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.6.3
[1.6.2]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.6.2
[1.6.1]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.6.1
[1.6.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.6.0
[1.5.0]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.5.0
[1.4.5]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.4.5
[1.4.4]: https://github.com/speechmatics/speechmatics-python/releases/tag/1.4.4
