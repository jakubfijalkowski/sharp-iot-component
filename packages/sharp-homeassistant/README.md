# Sharp IoT Home Assistant Integration

A Home Assistant integration for Sharp air purifiers and humidifiers that connects to Sharp's cloud API to provide complete device control and monitoring.

## Features

### Device Support
- **Multi-device support**: Automatically discovers all Sharp devices in your account
- **Air purifiers**: Complete control and monitoring of Sharp air purifier devices
- **Humidifiers**: Humidity control and monitoring for Sharp humidifier devices

### Entity Types

#### Fan Entity (Air Purifier Control)
- **Preset modes**: Auto, Sleep, Low, Medium, Max, Pollen, Ion Shower, Sharp Life Air
- **Real-time status**: Current operating mode
- **Availability**: Entity unavailable when device is powered off

#### Sensor Entities (Environmental Monitoring)
- **Temperature**: Current room temperature (°C)
- **Humidity**: Current humidity percentage (%)
- **PM2.5**: Particulate matter 2.5 levels (µg/m³)
- **Air Quality**: Quality level (0-4: Clean, Low, Medium, High, Very High)
- **Dust Level**: Dust sensor readings (0-4 scale)
- **Odor Level**: Odor sensor readings (0-4 scale)
- **Availability**: All sensors unavailable when device is powered off

#### Switch Entities (Device Controls)
- **Power**: Main device power control (always available)
- **Humidification**: Toggle humidification feature (unavailable when powered off)
- **Child Lock**: Enable/disable child safety lock (unavailable when powered off)
- **LED Brightness**: Control display brightness - Off/Dim/Auto (unavailable when powered off)

#### Binary Sensor (Status Indicators)
- **Water Level**: Problem state when water container is empty (unavailable when powered off)

## Installation

### Via HACS (Recommended)

1. **Add Custom Repository**:
   - Open HACS in Home Assistant
   - Go to **Integrations**
   - Click the three dots menu (⋮) in the top right
   - Select **Custom repositories**
   - Add the repository URL with category **Integration**
   - **Important**: Make sure to use the `hacs` branch (HACS should detect this automatically)

2. **Install the Integration**:
   - Search for "Sharp IoT" in HACS
   - Click **Download**
   - Restart Home Assistant

For detailed instructions on adding custom repositories to HACS, see: [HACS Documentation - Custom Repositories](https://hacs.xyz/docs/faq/custom_repositories/)

### Manual Installation

1. Copy `packages/sharp-homeassistant/src/custom_components/sharp_iot/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant

## Setup

### Prerequisites

You need a Sharp IoT terminal ID to use this integration. Get one by:

1. **Using the Authentication Server**:
   ```bash
   uv run sharp-auth
   ```

2. **Follow the OAuth flow**:
   - Server starts at http://localhost:8000 and opens automatically
   - Click "Start Authentication" to begin OAuth 2.0 flow
   - Log in with your Sharp account credentials
   - Copy the callback URL (`sharp-cocoroair-eu://authorize?code=...`) from the browser
   - Paste it into the authentication page
   - Copy the terminal ID from the success page

### Configuration

1. Go to **Settings** → **Devices & Services** in Home Assistant
2. Click **Add Integration**
3. Search for "Sharp IoT"
4. Enter your terminal ID when prompted
5. The integration will automatically discover and pair all your Sharp devices

## Usage

### Device Control

Each Sharp device appears with the following entities:

- **Fan Entity**: Control operating mode (auto, sleep, low, medium, max, pollen, ion_shower, sharp_life_air)
- **Power Switch**: Turn device on/off
- **Humidification Switch**: Toggle humidification feature
- **Child Lock Switch**: Enable/disable child safety lock
- **LED Brightness Switch**: Control display brightness
- **Environmental Sensors**: Temperature, humidity, PM2.5
- **Quality Sensors**: Air quality, dust level, odor level
- **Water Level Binary Sensor**: Alerts when water container is empty

### Update Interval

The integration polls devices every 30 seconds by default. After executing a command, it automatically refreshes the device state.

### Automation Examples

#### Auto Mode Based on Air Quality
```yaml
automation:
  - alias: "Auto Air Purifier Control"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sharp_1234_air_quality
        above: 2
    action:
      - service: fan.set_preset_mode
        target:
          entity_id: fan.sharp_air_purifier_1234
        data:
          preset_mode: "auto"
```

#### Humidity Control
```yaml
automation:
  - alias: "Auto Humidification Control"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sharp_1234_humidity
        below: 40
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.sharp_1234_humidification
```

#### Water Level Alert
```yaml
automation:
  - alias: "Low Water Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.sharp_1234_water_level
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Sharp air purifier water container is empty"
```

## Development and Testing

### Development Setup

```bash
# Install dependencies (from repository root)
uv sync

# Run authentication server to get terminal ID
uv run sharp-auth

# Test device operations with CLI
uv run sharp-cli <terminal_id>

# Copy integration to Home Assistant for testing
cp -r packages/sharp-homeassistant/src/custom_components/sharp_iot /path/to/homeassistant/custom_components/
```

## API Reference

The integration uses Sharp's EU cloud API endpoints:
- **Authentication**: `https://auth-eu.global.sharp/oxauth/restv1/`
- **Device API**: `https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/`

### Device Properties

- **F1 Property**: Environmental data (temperature, humidity, PM2.5)
- **F2 Property**: Quality sensors (air quality, dust, odor, water level)
- **F3 Property**: Device control state (power, mode, settings)

## Troubleshooting

### Common Issues

1. **Invalid Terminal ID**: Terminal IDs don't expire but may become invalid if the terminal is deleted. Run `uv run sharp-auth` to create a new terminal.
2. **No Devices Found**: Devices must be registered in Sharp's cloud first. Use the official Sharp app to set up devices, then they'll be discovered automatically.
3. **Connection Errors**: Verify internet connectivity and Sharp service status. The integration requires continuous internet access.
4. **Entities Unavailable**: Most entities become unavailable when the device is powered off. Only the power switch remains available.

### Debug Logging

Enable debug logging in Home Assistant configuration:

```yaml
logger:
  default: info
  logs:
    custom_components.sharp_iot: debug
    sharp_core: debug
    sharp_devices: debug
```

### Support

For issues and support:
1. Check Home Assistant logs: Settings → System → Logs
2. Verify device connectivity in the official Sharp app
3. Test with the CLI tool: `uv run sharp-cli <terminal_id>`
4. Report issues with debug logs and anonymized device IDs

## License

This integration is provided as-is for educational and personal use. Sharp IoT is a trademark of Sharp Corporation.