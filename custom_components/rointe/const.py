from homeassistant.const import Platform

DOMAIN = "rointe"
PLATFORMS = [Platform.CLIMATE, Platform.SWITCH]

# Device types
DEVICE_TYPE_RADIATOR = "radiator"
DEVICE_TYPE_TOWEL_RAIL = "towel_rail"
DEVICE_TYPE_THERMOSTAT = "thermostat"
DEVICE_TYPE_OVAL_TOWEL = "oval_towel"

# Sensor types
SENSOR_TYPE_POWER = "power"
SENSOR_TYPE_ENERGY = "energy"
SENSOR_TYPE_CURRENT_TEMP = "current_temperature"

# Binary sensor types
BINARY_SENSOR_TYPE_FIRMWARE_UPDATE = "firmware_update"

# Device model mappings
DEVICE_MODELS = {
    "Series-D": DEVICE_TYPE_RADIATOR,
    "Belize": DEVICE_TYPE_RADIATOR,
    "Olympia": DEVICE_TYPE_RADIATOR,
    "Towel": DEVICE_TYPE_TOWEL_RAIL,
    "Oval": DEVICE_TYPE_OVAL_TOWEL,
    "Thermostat": DEVICE_TYPE_THERMOSTAT,
}