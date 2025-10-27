# Changelog

All notable changes to the Rointe Nexa integration will be documented in this file.

## [0.0.8] - 2024-01-XX
### Added
- **Energy Consumption Sensors**: Power consumption (watts) and energy consumption (kWh) sensors
- **Firmware Update Detection**: Binary sensor to notify when firmware updates are available
- **Additional Device Types**: Support for towel rails, thermostats, and oval towel warmers
- **Enhanced Device Information**: Serial numbers, MAC addresses, zone information, and device status
- **Sensor Platform**: New sensor.py platform for energy and temperature monitoring
- **Binary Sensor Platform**: New binary_sensor.py platform for firmware update notifications
- **Device Type Detection**: Automatic categorization of devices (radiator, towel_rail, thermostat, oval_towel)

### Enhanced
- **Device Discovery**: Now extracts energy consumption and firmware update data from API
- **Climate Entities**: Enhanced with device category, serial number, MAC address, and zone information
- **API Response Parsing**: Extended to include energy consumption, firmware updates, and device status
- **Device Registry Integration**: Better device information for Home Assistant device registry

### Technical
- Added device type constants and mappings in const.py
- Enhanced API device_info extraction with energy and firmware fields
- Improved WebSocket update handling for new sensor data
- Added comprehensive device status tracking

## [0.0.7] - 2024-01-XX
### Fixed
- Fixed device discovery - integration now properly finds Rointe devices
- Corrected API response parsing for installations endpoint
- Fixed zone processing (devices are nested directly in zones)
- Added automated GitHub release workflows for HACS update notifications
- Integration now discovers devices: "Rad. 6062EC" in "Utility" zone

## [0.0.5] - 2024-01-XX
### Fixed
- Resolved "cannot import name 'temp_celcuis'" error
- Fixed temperature unit compatibility across Home Assistant versions
- Updated HACS.json format for proper repository detection

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
