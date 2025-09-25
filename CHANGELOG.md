# Changelog

All notable changes to the Rointe Nexa integration will be documented in this file.

## [0.0.4] - 2024-01-XX
### Simplified
- Removed redundant preset modes (duplicated HVAC functionality)
- Simplified HVAC modes from 4 to 2 (OFF and HEAT only)
- Removed unused DEFAULT_MIN_TEMP and DEFAULT_MAX_TEMP constants
- Cleaner temperature range configuration
- Improved Home Assistant compatibility across all versions

### Fixed
- Resolved "cannot import name 'presetmode'" error
- Better compatibility with older Home Assistant versions

## [0.0.3] - 2024-01-XX
### Added
- Enhanced authentication system with dual REST API and Firebase support
- Improved error handling for HTTP 418 responses
- Browser-like headers to prevent bot detection
- Comprehensive device information display
- Enhanced HVAC modes and preset support

### Fixed
- Authentication compatibility issues
- Climate entity import compatibility with newer Home Assistant versions
- WebSocket reconnection reliability

## [0.0.2] - 2024-01-XX
### Added
- Initial dual authentication system
- Enhanced error handling
- Device information support

## [0.0.1] - 2024-01-XX
### Added
- Initial release
- Basic Rointe Nexa integration
- Climate control functionality
