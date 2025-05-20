# Sharp IoT Device Control

> **⚠️ IMPORTANT DISCLAIMER**: This repository and its code are almost fully AI-generated. I take no responsibility for the code quality, accuracy, or functionality. The documentation (including READMEs) may contain errors or inaccuracies. While the plugin should work, **proceed with caution** and review the code yourself before use. I checked the code, but am not proficient in Python. As for the READMEs, I barely looked at them. :)
>
> **Note on Protocol Reverse Engineering**: The Sharp IoT protocol was reverse-engineered for personal purposes in good faith. This work was done mostly manually through network traffic analysis, as AI tools were barely helpful for this particular task.
>
> **Branch Info**: This is the development branch (`master`). For HACS installation, use the `hacs` branch.

A comprehensive Python workspace for controlling Sharp air purifiers and humidifiers via their cloud API. This project implements a reverse-engineered protocol that combines OAuth 2.0 authentication with EchoNet Lite device communication.

## Features

- 🔐 **OAuth 2.0 Authentication**: FastAPI web server for terminal registration
- 🏠 **Home Assistant Integration**: Full-featured custom component with multiple platforms
- 💻 **Command-Line Interface**: Simple CLI tool for device control and testing
- 📦 **Modular Architecture**: Clean separation with uv workspace packages
- 🌍 **EU Region Support**: Optimized for Sharp's EU cloud services

## Architecture

This project uses a **uv workspace** with five packages:

```
sharp-iot-workspace/
├── packages/
│   ├── sharp-core/          # HTTP client and state enumerations
│   ├── sharp-auth/          # FastAPI OAuth 2.0 authentication server
│   ├── sharp-devices/       # Device operations and command construction
│   ├── sharp-cli/           # Command-line interface
│   └── sharp-homeassistant/ # Home Assistant custom component
├── CLAUDE.md                # Development documentation
└── README.md                # This file
```

### Package Dependencies

```
sharp-cli ──────► sharp-devices ──► sharp-core
                        ▲
sharp-homeassistant ────┘

sharp-auth ────────────► sharp-core
```

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Sharp IoT account (EU region)
- Sharp air purifier/humidifier connected to Sharp cloud

### Installation

```bash
# Clone repository
git clone <repository-url>
cd sharp/client

# Install all dependencies
uv sync
```

### Get Terminal ID

First, obtain a terminal ID using the authentication server:

```bash
# Start authentication server
uv run sharp-auth
```

The server will:
1. Open at `http://localhost:8000` in your browser
2. Guide you through Sharp's OAuth 2.0 flow
3. Provide a terminal ID on successful authentication

**Important**: Keep your terminal ID secure - it provides access to your devices.

### Test with CLI

```bash
# Test device connectivity
uv run sharp-cli <your-terminal-id>
```

This will:
- Authenticate with Sharp API
- Discover all devices on your account
- Display device properties (temperature, humidity, PM2.5, etc.)

### Install Home Assistant Integration

```bash
# Copy integration to Home Assistant
cp -r packages/sharp-homeassistant/src/custom_components/sharp_iot \
      /path/to/homeassistant/custom_components/

# Restart Home Assistant
# Then add integration via UI: Settings → Devices & Services → Add Integration → "Sharp IoT"
```

## Usage

### Authentication Server

Start the web-based authentication server:

```bash
uv run sharp-auth
```

Features:
- Multi-session support
- Real-time status updates
- RESTful API endpoints
- Automatic terminal registration

**See**: [packages/sharp-auth/README.md](packages/sharp-auth/README.md)

### Command-Line Interface

Control devices from the terminal:

```bash
# Display device properties
uv run sharp-cli <terminal-id>
```

Current CLI shows:
- Environmental sensors (temperature, humidity, PM2.5)
- Quality sensors (air quality, dust, odor, water level)
- Control state (power, mode, humidification, child lock, LED)

**See**: [packages/sharp-cli/README.md](packages/sharp-cli/README.md)

### Home Assistant Integration

Full-featured integration with:

**Platforms:**
- **Fan**: Operating mode control (auto, sleep, low, medium, max, pollen, ion_shower, sharp_life_air)
- **Sensors**: Temperature, humidity, PM2.5, air quality, dust level, odor level
- **Switches**: Power, humidification, child lock, LED brightness
- **Binary Sensors**: Water level alerts

**Features:**
- Automatic device discovery
- 30-second polling interval
- Config flow UI setup
- Availability tracking (entities unavailable when powered off)

**See**: [packages/sharp-homeassistant/README.md](packages/sharp-homeassistant/README.md)

## Device Control Examples

### Python API

```python
from sharp_core import SharpClient
from sharp_core.states import *
from sharp_devices.operations import SharpOperations
from sharp_devices.device_control import *

# Initialize
client = SharpClient()
ops = SharpOperations(client)

# Authenticate
terminal_id = "your-terminal-id"
ops.setup_with_terminal_id(terminal_id)

# Discover devices
devices = ops.discover_and_pair_devices(terminal_id)
device = devices[0]

# Turn on and set to auto mode
ops.execute_operation(device, terminal_id, PowerOperation(PowerState.ON))
ops.execute_operation(device, terminal_id, ChangeModeCommand(OperatingMode.AUTO))

# Enable humidification
ops.execute_operation(device, terminal_id, HumidificationCommand(HumidificationState.ON))

# Read current state
props = ops.get_device_properties(device)
print(f"Temperature: {props.f1_property.temperature}°C")
print(f"Humidity: {props.f1_property.humidity}%")
print(f"Mode: {props.f3_property.operating_mode.name}")
```

**See**: [packages/sharp-devices/README.md](packages/sharp-devices/README.md)

### Home Assistant Automation

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

## Protocol Details

### Authentication Flow

1. **Get Terminal App ID**: Request new terminal from Sharp API
2. **OAuth 2.0 Login**: User authenticates with Sharp account
3. **Token Exchange**: Exchange authorization code for access token
4. **Terminal Registration**: Register terminal with random 5-char name

### Device Communication

Sharp devices use a hierarchical structure:

```
Terminal → Box (Gateway) → Device → Properties
```

**Device Properties:**
- **F1**: Environmental data (temperature, humidity, PM2.5)
- **F2**: Quality sensors (air quality, dust, odor, water level)
- **F3**: Control state (power, mode, settings)

**Command Format:**
- **Status 80**: Simple power control (`valueSingle`)
- **Status F3**: Binary control commands (`valueBinary`, 54-char hex payload)

### API Endpoints

- **Auth Server**: `https://auth-eu.global.sharp/oxauth/restv1/`
- **Device API**: `https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/`

### Command Execution

Commands follow a two-phase async process:

1. **Submit**: POST command to `/control/deviceControl` → receive operation ID
2. **Poll**: POST operation ID to `/control/controlResult` (10 attempts, 1s intervals)
3. **Success**: Status becomes "success" or "unmatch" with no error code

## Development

### Project Structure

```
packages/
├── sharp-core/              # Foundation layer
│   ├── src/sharp_core/
│   │   ├── client.py        # HTTP client with auth headers
│   │   └── states.py        # Device state enumerations
│   └── README.md
│
├── sharp-auth/              # Authentication layer
│   ├── src/sharp_auth/
│   │   └── auth_server.py   # FastAPI OAuth server
│   ├── templates/
│   │   └── auth.html        # Web UI
│   └── README.md
│
├── sharp-devices/           # Device control layer
│   ├── src/sharp_devices/
│   │   ├── operations.py          # Device lifecycle ops
│   │   ├── device_control.py      # Command construction
│   │   └── device_properties.py   # Property parsing
│   └── README.md
│
├── sharp-cli/               # CLI interface
│   ├── src/sharp_cli/
│   │   └── main.py          # Command-line tool
│   └── README.md
│
└── sharp-homeassistant/     # Home Assistant integration
    ├── src/custom_components/sharp_iot/
    │   ├── __init__.py           # Integration setup
    │   ├── config_flow.py        # UI configuration
    │   ├── coordinator.py        # Data update coordinator
    │   ├── const.py              # Constants
    │   ├── fan.py                # Fan platform
    │   ├── sensor.py             # Sensor platform
    │   ├── switch.py             # Switch platform
    │   └── binary_sensor.py      # Binary sensor platform
    └── README.md
```

### Adding New Commands

1. **Define state enum** in `sharp-core/src/sharp_core/states.py`
2. **Create command class** in `sharp-devices/src/sharp_devices/device_control.py`
3. **Use in operations** via `execute_operation()`

Example:
```python
# 1. Add state enum
class NewFeatureState(Enum):
    OFF = "00"
    ON = "FF"

# 2. Create command
class NewFeatureCommand(DeviceStatusCommand):
    def __init__(self, state: NewFeatureState):
        super().__init__()
        self.state = state

    def get_header(self) -> str:
        return "00100000"  # Your header

    def get_payload_position(self) -> int:
        return 30  # Your position

    def get_payload_value(self) -> str:
        return self.state.value

# 3. Use command
operations.execute_operation(device, terminal_id, NewFeatureCommand(NewFeatureState.ON))
```

### Running Tests

```bash
# Test all packages
uv run python -c "
from sharp_core import SharpClient
from sharp_devices.operations import SharpOperations
from sharp_devices.device_control import PowerOperation
from sharp_auth.auth_server import app
print('All imports successful')
"

# Test with real device
uv run sharp-cli <terminal-id>
```

### Code Conventions

- **Type hints**: Use throughout (`Dict[str, Any]`, `Optional[str]`, `List[BoxInfo]`)
- **Dataclasses**: For structured data (`@dataclass`)
- **Error handling**: `raise_for_status()` for HTTP errors
- **Logging**: Module-level logger `_LOGGER = logging.getLogger(__name__)`
- **Async patterns**: Home Assistant uses `hass.async_add_executor_job()`

## Troubleshooting

### Authentication Issues

**Invalid Terminal ID**:
- Terminal IDs don't expire but can be invalidated
- Solution: Run `uv run sharp-auth` to create new terminal

**OAuth Callback Failed**:
- Browser must show `sharp-cocoroair-eu://authorize?code=...`
- Copy entire URL including the code parameter
- Paste into authentication page

### Device Discovery Issues

**No Devices Found**:
- Devices must be set up in official Sharp app first
- Ensure devices are online and connected to Sharp cloud
- Check internet connectivity

**Pairing Failed**:
- Device may already be paired to another terminal
- Try unpairing in Sharp app, then rediscover

### Connection Issues

**API Errors**:
- Verify internet connectivity
- Check Sharp service status
- Ensure correct API endpoints for EU region

**Timeout During Command Execution**:
- Device may be offline
- Network latency may be high
- Command may not be supported by device model

### Debug Logging

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

For Home Assistant:
```yaml
logger:
  default: info
  logs:
    custom_components.sharp_iot: debug
    sharp_core: debug
    sharp_devices: debug
```

## Package Documentation

Each package has detailed documentation:

- [sharp-core](packages/sharp-core/README.md) - HTTP client and state enumerations
- [sharp-auth](packages/sharp-auth/README.md) - OAuth authentication server
- [sharp-devices](packages/sharp-devices/README.md) - Device operations and commands
- [sharp-cli](packages/sharp-cli/README.md) - Command-line interface
- [sharp-homeassistant](packages/sharp-homeassistant/README.md) - Home Assistant integration

## Developer Documentation

See [CLAUDE.md](CLAUDE.md) for comprehensive technical documentation including:
- Complete protocol specifications
- Command structure details
- Property parsing byte positions
- State enum values
- Code conventions

## Contributing

This is a reverse-engineered protocol implementation. Contributions welcome:

1. Device testing with different Sharp models
2. Additional command implementations
3. Enhanced CLI features
4. Bug fixes and improvements

## Compatibility

**Tested Devices:**
- Sharp air purifiers with cloud connectivity (EU region)
- Sharp air purifier/humidifier combos (EU region)

**Requirements:**
- Python 3.13+
- uv package manager
- Internet connection for Sharp cloud API

**Supported Platforms:**
- Linux
- macOS
- Windows (with WSL recommended)

## Known Limitations

- **EU Region Only**: Designed for Sharp's EU cloud services
- **Cloud Dependent**: Requires internet connection, no local control
- **Limited CLI**: CLI currently read-only (control can be added)
- **No State Push**: Integration polls every 30 seconds (no real-time updates)

## License

This project is provided as-is for educational and personal use.

**Disclaimer**: This is an unofficial implementation based on reverse engineering. Sharp IoT is a trademark of Sharp Corporation. This project is not affiliated with or endorsed by Sharp Corporation.

## Acknowledgments

This project reverse-engineers Sharp's cloud API protocol to enable local automation and control of Sharp IoT devices.

## Support

For issues and questions:
1. Check package-specific README files
2. Enable debug logging
3. Test with CLI tool: `uv run sharp-cli <terminal-id>`
4. Verify devices work in official Sharp app
5. Open an issue with logs and device details (anonymized)
