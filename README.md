# Home Assistant Rointe Nexa Integration

Custom integration for controlling Rointe radiators via the Nexa cloud.

## Installation

1. Copy `custom_components/rointe/` into your Home Assistant `/config/custom_components/` folder.
2. Restart Home Assistant.
3. You should see a dummy climate entity called **Rointe Dummy Heater** under `climate.rointe_dummy_heater`.

## Development Roadmap

- [x] Skeleton integration (dummy climate entity)
- [ ] Login with Firebase (`signInWithPassword`)
- [ ] Token refresh via Google `securetoken.googleapis.com`
- [ ] WebSocket subscription to Firebase RTDB
- [ ] Live state → HA climate entity
- [ ] Send control commands (comfort, eco, off, set temperature)
- [ ] Optional: schedules and advanced features