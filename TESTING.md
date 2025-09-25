# 🧪 Rointe Integration Testing Guide

This guide covers different ways to test the Rointe HACS integration locally.

## 🚀 Quick Start Testing

### Option 1: Docker-based Home Assistant (Recommended)

The easiest way to test with a real Home Assistant environment:

```bash
# Run the setup script
python test_setup.py

# Choose option 1 (Docker-based HA)
# Follow the prompts to set up Docker Home Assistant

# Start Home Assistant
docker-compose up -d

# Access Home Assistant
# Open: http://localhost:8123
```

**Steps to test:**
1. Complete Home Assistant initial setup
2. Go to **Settings → Devices & Services → Add Integration**
3. Search for **"Rointe"**
4. Enter your Rointe Nexa credentials
5. Verify devices appear as climate entities

### Option 2: Python Virtual Environment

For development with Home Assistant core:

```bash
# Run the setup script
python test_setup.py

# Choose option 2 (Python HA)
# Follow the prompts to set up virtual environment

# Activate environment (Windows)
ha_test_env\Scripts\activate

# Start Home Assistant
hass --open-ui
```

## 🔧 Manual Testing Steps

### 1. Configuration Flow Testing

Test the setup process:

1. **Valid Credentials:**
   - Use your real Rointe Nexa email/password
   - Should complete setup successfully
   - Should show "Rointe Nexa (your-email@domain.com)"

2. **Invalid Email Format:**
   - Try: "invalid-email"
   - Should show: "Please enter a valid email address"

3. **Short Password:**
   - Try: "12345"
   - Should show: "Password must be at least 6 characters long"

4. **Wrong Credentials:**
   - Try: "test@example.com" / "wrongpassword"
   - Should show: "Invalid email or password"

### 2. Device Discovery Testing

After successful setup:

1. **Check Logs:**
   ```
   # In Home Assistant logs, look for:
   - "Starting device discovery"
   - "Found X installations"
   - "Discovered X devices"
   ```

2. **Verify Entities:**
   - Go to **Settings → Devices & Services → Entities**
   - Look for entities named: "Zone Name - Device Name"
   - Check entity states and attributes

### 3. Climate Entity Testing

Test each HVAC mode:

1. **OFF Mode:**
   - Set HVAC mode to "Off"
   - Temperature should show 7°C
   - Device should enter "ice" mode

2. **HEAT Mode:**
   - Set HVAC mode to "Heat"
   - Temperature range should be 15-35°C
   - Device should enter "comfort" mode

3. **AUTO Mode:**
   - Set HVAC mode to "Auto"
   - Should map to "comfort" mode
   - Temperature range should be 15-35°C

4. **HEAT_COOL Mode:**
   - Set HVAC mode to "Heat/Cool"
   - Should map to "eco" mode
   - Temperature range should be 15-35°C

### 4. Preset Mode Testing

Test preset modes:

1. **Comfort Preset:**
   - Set preset to "Comfort"
   - HVAC mode should change to "Heat"
   - Device should enter "comfort" mode

2. **Eco Preset:**
   - Set preset to "Eco"
   - HVAC mode should change to "Eco"
   - Device should enter "eco" mode

### 5. Temperature Control Testing

Test temperature setting:

1. **Valid Temperature:**
   - Set temperature to 21°C (should work)
   - Set temperature to 25°C (should work)

2. **Invalid Temperature:**
   - In OFF mode, try to set 15°C (should fail)
   - In HEAT mode, try to set 5°C (should fail)

### 6. WebSocket Testing

Test real-time updates:

1. **Change device via Rointe app:**
   - Change temperature in Rointe mobile app
   - HA should update within seconds

2. **Change device via HA:**
   - Change temperature in HA
   - Rointe app should update within seconds

## 🐛 Debugging

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.rointe: debug
```

### Common Issues

1. **"Authentication failed":**
   - Check credentials are correct
   - Verify Rointe account is active
   - Check internet connection

2. **"No devices discovered":**
   - Verify you have devices in Rointe app
   - Check API connection
   - Review logs for API errors

3. **"WebSocket connection failed":**
   - Check firewall settings
   - Verify internet connection
   - Check if Rointe services are down

### Log Analysis

Look for these log patterns:

**Successful Setup:**
```
INFO: Authentication successful
INFO: WebSocket connection established
INFO: Device discovery completed: found X devices
INFO: Rointe integration setup completed successfully
```

**Error Patterns:**
```
ERROR: Authentication failed: [details]
ERROR: Device discovery failed: [details]
ERROR: WebSocket connection failed: [details]
```

## 🧪 Automated Testing

### Run Mock Tests

```bash
python tests/mock_test.py
```

### Run Integration Tests

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run tests
python -m pytest tests/ -v
```

## 📊 Testing Checklist

- [ ] Configuration flow works with valid credentials
- [ ] Configuration flow shows proper errors for invalid inputs
- [ ] Device discovery finds all devices
- [ ] Climate entities appear with correct names
- [ ] All HVAC modes work correctly
- [ ] All preset modes work correctly
- [ ] Temperature setting works within valid ranges
- [ ] Temperature validation prevents invalid values
- [ ] WebSocket updates work in real-time
- [ ] Device information is displayed correctly
- [ ] Error handling works for network issues
- [ ] Integration unloads cleanly

## 🚨 Troubleshooting

### Home Assistant Won't Start

1. Check Docker is running
2. Check port 8123 is available
3. Review Docker logs: `docker-compose logs homeassistant`

### Integration Not Found

1. Verify integration is in `custom_components/rointe/`
2. Restart Home Assistant
3. Check `custom_components` directory permissions

### Devices Not Appearing

1. Check Rointe credentials
2. Verify devices exist in Rointe app
3. Enable debug logging and check logs
4. Test API connectivity

### WebSocket Issues

1. Check firewall settings
2. Verify internet connection
3. Check if Rointe services are accessible
4. Review WebSocket connection logs

## 📝 Test Results Template

```
Test Date: [DATE]
Home Assistant Version: [VERSION]
Python Version: [VERSION]
Integration Version: [VERSION]

Configuration Flow:
- [ ] Valid credentials work
- [ ] Invalid email format rejected
- [ ] Short password rejected
- [ ] Wrong credentials rejected

Device Discovery:
- [ ] X devices found
- [ ] Device names correct
- [ ] Device information complete

Climate Functionality:
- [ ] All HVAC modes work
- [ ] All preset modes work
- [ ] Temperature setting works
- [ ] Temperature validation works
- [ ] Real-time updates work

Issues Found:
- [List any issues]

Overall Result: [PASS/FAIL]
```
