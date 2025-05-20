# Sharp CLI

Command-line interface for Sharp IoT air purifier and humidifier control.

## Overview

`sharp-cli` provides a simple command-line tool for interacting with Sharp IoT devices. It's useful for testing device connectivity, debugging API interactions, and quick device control without a full integration.

## Installation

Install as part of the Sharp IoT workspace:

```bash
uv sync
```

## Usage

### Basic Command

```bash
uv run sharp-cli <terminal-id>
```

Where `<terminal-id>` is obtained from the authentication server.

### Get Terminal ID

First, run the authentication server to get a terminal ID:

```bash
# Start auth server
uv run sharp-auth

# Follow OAuth flow in browser
# Copy terminal ID from success page
```

### Example Session

```bash
$ uv run sharp-cli abc123def456

Using terminalAppId: abc123def456

Device Properties:
Properties for box 1234567890abcdef:
F1(temp=22°C, hum=45%, pm25=12)
F2(air=CLEAN, dust=CLEAN, odor=CLEAN, water=FULL)
F3(mode=AUTO, hum=ON, pwr=ON, lock=OFF, led=AUTO)
```

## Current Functionality

The CLI currently:
1. Authenticates with Sharp API using terminal ID
2. Discovers all devices on the account
3. Automatically pairs any unpaired devices
4. Refreshes device state
5. Displays properties for all discovered devices

## Device Properties Display

### F1 Property (Environmental)
- **temp**: Temperature in Celsius
- **hum**: Humidity percentage
- **pm25**: PM2.5 level in μg/m³

### F2 Property (Quality Sensors)
- **air**: Air quality level (CLEAN, LOW, MEDIUM, HIGH, VERY_HIGH)
- **dust**: Dust sensor level
- **odor**: Odor sensor level
- **water**: Water container state (UNKNOWN, FULL, EMPTY)

### F3 Property (Control State)
- **mode**: Operating mode (OFF, LOW, MED, MAX, AUTO, POLLEN, ION_SHOWER, SLEEP, SHARP_LIFE_AIR)
- **hum**: Humidification state (ON/OFF)
- **pwr**: Power state (ON/OFF)
- **lock**: Child lock state (ON/OFF)
- **led**: LED brightness (OFF, DIM, AUTO)

## Exit Codes

- `0`: Success
- `1`: Error (setup failed, no devices found, etc.)

## Error Messages

### Usage Error
```
Usage: python main.py <terminalAppId>

To get a terminal ID, run the authentication server:
  uv run sharp-auth
Then complete the authentication process in your browser.
```

### Setup Failed
```
Error: Setup with terminal ID failed
```

Possible causes:
- Invalid terminal ID
- Network connectivity issues
- Sharp API service issues

## Implementation Details

The CLI uses:
- `sharp-core.SharpClient`: HTTP client for API communication
- `sharp-devices.SharpOperations`: Device discovery and control
- `sharp-devices.device_control.RefreshStateOperation`: State refresh without commands

### Code Flow

```python
# 1. Parse command line arguments
terminal_app_id = sys.argv[1]

# 2. Initialize client and operations
client = SharpClient()
operations = SharpOperations(client)

# 3. Authenticate
operations.setup_with_terminal_id(terminal_app_id)

# 4. Discover and pair devices
box_infos = operations.discover_and_pair_devices(terminal_app_id)

# 5. Refresh state
operations.execute_operation(box_infos[0], terminal_app_id, RefreshStateOperation())

# 6. Get and display properties
for box_info in box_infos:
    properties = operations.get_device_properties(box_info)
    print(properties)
```

## Extending the CLI

The CLI can be extended to support interactive device control:

### Example: Add Device Control

```python
import sys
from sharp_core import SharpClient
from sharp_core.states import *
from sharp_devices.operations import SharpOperations
from sharp_devices.device_control import *

def main():
    if len(sys.argv) < 2:
        print("Usage: sharp-cli <terminal-id> [command] [args]")
        return 1

    terminal_id = sys.argv[1]

    # Initialize
    client = SharpClient()
    ops = SharpOperations(client)
    ops.setup_with_terminal_id(terminal_id)
    devices = ops.discover_and_pair_devices(terminal_id)

    if len(sys.argv) == 2:
        # Display properties (current behavior)
        for device in devices:
            props = ops.get_device_properties(device)
            print(props)
    else:
        # Handle commands
        command = sys.argv[2]
        device = devices[0]  # Use first device

        if command == "on":
            ops.execute_operation(device, terminal_id, PowerOperation(PowerState.ON))
            print("Device turned on")

        elif command == "off":
            ops.execute_operation(device, terminal_id, PowerOperation(PowerState.OFF))
            print("Device turned off")

        elif command == "mode" and len(sys.argv) > 3:
            mode_map = {
                "auto": OperatingMode.AUTO,
                "sleep": OperatingMode.SLEEP,
                "low": OperatingMode.LOW,
                "med": OperatingMode.MED,
                "max": OperatingMode.MAX,
            }
            mode = mode_map.get(sys.argv[3])
            if mode:
                ops.execute_operation(device, terminal_id, ChangeModeCommand(mode))
                print(f"Mode set to {sys.argv[3]}")
            else:
                print(f"Unknown mode: {sys.argv[3]}")

        else:
            print("Unknown command")
            print("Available commands: on, off, mode <auto|sleep|low|med|max>")

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Usage examples:
```bash
# Display properties
uv run sharp-cli abc123

# Turn on device
uv run sharp-cli abc123 on

# Change mode
uv run sharp-cli abc123 mode auto

# Turn off device
uv run sharp-cli abc123 off
```

## Debugging

### Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Test API Connectivity

```python
from sharp_core import SharpClient

client = SharpClient()
try:
    response = client.get("https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/boxInfo",
                         params={"mode": "other"})
    print("API accessible")
except Exception as e:
    print(f"API error: {e}")
```

## Dependencies

- `sharp-devices`: Device operations and control
- `sharp-core`: HTTP client (via sharp-devices)
- `sharp-core.states`: State enumerations (via sharp-devices)

## Entry Point

The CLI is registered as a console script in `pyproject.toml`:

```toml
[project.scripts]
sharp-cli = "sharp_cli.main:main"
```

This allows running via:
```bash
uv run sharp-cli <terminal-id>
```

## Development

```bash
# Install workspace
uv sync

# Run directly
uv run python packages/sharp-cli/src/sharp_cli/main.py <terminal-id>

# Or via entry point
uv run sharp-cli <terminal-id>
```

## Comparison with Other Interfaces

| Feature | CLI | Auth Server | Home Assistant |
|---------|-----|-------------|----------------|
| Device Discovery | ✓ | ✗ | ✓ |
| Property Display | ✓ | ✗ | ✓ |
| Device Control | Limited | ✗ | Full |
| Authentication | Requires terminal ID | Provides terminal ID | Requires terminal ID |
| User Interface | Terminal | Web Browser | Web Dashboard |
| Automation | Shell scripts | N/A | Built-in |
| Real-time Updates | Manual refresh | N/A | Auto polling |

## Use Cases

- **Testing**: Verify device connectivity and API responses
- **Debugging**: Troubleshoot authentication and discovery issues
- **Development**: Quick iteration when developing new features
- **Scripting**: Integrate with shell scripts for automation
- **Diagnostics**: Check device properties and state

## Troubleshooting

### Command Not Found
```bash
# Make sure workspace is installed
uv sync

# Try full path
uv run python packages/sharp-cli/src/sharp_cli/main.py <terminal-id>
```

### Setup Failed
Check that:
1. Terminal ID is valid (from `uv run sharp-auth`)
2. Internet connection is working
3. Sharp API services are available

### No Devices Found
Ensure:
1. Devices are set up in the official Sharp app
2. Devices are online and connected to Sharp cloud
3. Terminal ID has access to the devices

## License

Part of the Sharp IoT device control workspace. Sharp IoT is a trademark of Sharp Corporation.
