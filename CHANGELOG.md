# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.1] - 2025-11-26

### Changed

- Refactored integration to use the [pymoogo](https://github.com/joyfulhouse/pymoogo) library for all API interactions.
- Improved code quality and maintainability throughout.
- Updated CI workflows for pymoogo-based architecture.

### Added

- Exponential backoff retry logic for device operations.
- HACS and Hassfest GitHub Actions validation workflows.
- Platinum Tier Home Assistant Quality Scale implementation.

## [2.0.0] - 2025-11-26

### Added

- Major refactor: pymoogo library replaces the bundled API client.
- Full switch entity support for start/stop mosquito misting.
- Device registry integration with firmware version tracking.

## [1.5.1] - 2025-11-26

### Fixed

- Minor bug fixes and stability improvements.

## [1.0.0] - 2025-11-26

### Added

- Initial release with public and authenticated sensor data.
- Config flow supporting full-access and public-data-only modes.
- DataUpdateCoordinator with 30-second polling for device data.

<!-- Version comparison links -->
[Unreleased]: https://github.com/joyfulhouse/moogo/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/joyfulhouse/moogo/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/joyfulhouse/moogo/compare/v1.5.1...v2.0.0
[1.5.1]: https://github.com/joyfulhouse/moogo/compare/v1.0.0...v1.5.1
[1.0.0]: https://github.com/joyfulhouse/moogo/releases/tag/v1.0.0
