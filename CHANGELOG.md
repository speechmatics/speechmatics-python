# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Use later version of sphinx to generate docs (supports Python 3.10)
- Update Speechmatics logo

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
