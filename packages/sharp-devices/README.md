# Sharp Devices

Device operations, control commands, and property parsing for Sharp IoT air purifiers and humidifiers.

## Overview

`sharp-devices` provides the core functionality for interacting with Sharp IoT devices through their cloud API. It implements the EchoNet Lite protocol for device communication, including command construction, operation execution, and property parsing.

## Components

### SharpOperations

Main class for device operations and lifecycle management.

**Key Methods:**

#### setup_with_terminal_id(terminal_app_id: str) -> bool
Authenticate with Sharp API using an existing terminal ID.

```python
from sharp_core import SharpClient
from sharp_devices.operations import SharpOperations

client = SharpClient()
operations = SharpOperations(client)
operations.setup_with_terminal_id("your-terminal-id")
```

#### discover_and_pair_devices(terminal_app_id: str) -> List[BoxInfo]
Discover all devices and automatically pair any unpaired ones.

```python
devices = operations.discover_and_pair_devices(terminal_app_id)
for device in devices:
    print(f"Found: {device.box_id} at {device.echonet_node}")
```

#### get_device_properties(box_info: BoxInfo) -> DeviceProperties
Fetch and parse current device state.

```python
properties = operations.get_device_properties(device)
print(f"Temperature: {properties.f1_property.temperature}°C")
print(f"Mode: {properties.f3_property.operating_mode.name}")
```

#### execute_operation(box_info: BoxInfo, terminal_app_id: str, operation: Operation) -> bool
Execute an operation on a device with automatic status polling.

```python
from sharp_devices.device_control import PowerOperation, ChangeModeCommand
from sharp_core.states import PowerState, OperatingMode

# Turn on device
operations.execute_operation(device, terminal_id, PowerOperation(PowerState.ON))

# Change operating mode
operations.execute_operation(device, terminal_id, ChangeModeCommand(OperatingMode.AUTO))
```

### BoxInfo

Dataclass representing a device gateway with connection details.

```python
@dataclass
class BoxInfo:
    box_id: str              # Unique device identifier
    echonet_node: str        # EchoNet node address
    echonet_object: str      # EchoNet object code
    deviceId: str            # Device ID for commands
    terminals: List[str]     # Associated terminal IDs
```

## Device Properties

### DeviceProperties

Container for all device properties parsed from API responses.

```python
@dataclass
class DeviceProperties:
    echonet_node: str
    label: str
    f1_property: Optional[F1Property]  # Environmental data
    f2_property: Optional[F2Property]  # Quality sensors
    f3_property: Optional[F3Property]  # Control state
```

### F1Property - Environmental Data

Temperature, humidity, and PM2.5 readings.

```python
@dataclass
class F1Property:
    temperature: int    # Celsius
    humidity: int       # Percentage
    pm25_level: int     # μg/m³
```

**Parsing:** Hex string → bytes, extract:
- Temperature: byte at position 3
- Humidity: byte at position 4
- PM2.5: 2 bytes at positions 28-30 (little-endian)

### F2Property - Quality Sensors

Air quality levels and water container status.

```python
@dataclass
class F2Property:
    air_quality: QualityLevel
    dust_level: QualityLevel
    odor_level: QualityLevel
    water_container: WaterContainerState
```

**Parsing:** Hex string → bytes, extract:
- Odor: byte at position 14 → QualityLevel.parse()
- Dust: byte at position 15 → QualityLevel.parse()
- Air Quality: byte at position 17 → QualityLevel.parse()
- Water Container: byte at position 18 → WaterContainerState.parse()

### F3Property - Control State

Current device operating state.

```python
@dataclass
class F3Property:
    operating_mode: OperatingMode
    humidification: HumidificationState
    power: PowerState
    child_lock: ChildLockState
    led_brightness: LEDBrightnessState
```

**Parsing:** 54-char hex string (8-char header + 46-char payload):
- Operating Mode: position 8-10 (payload position 0)
- Power: position 26-28 (payload position 18)
- Humidification: position 30-32 (payload position 22)
- Child Lock: position 36-38 (payload position 28)
- LED Brightness: position 52-54 (payload position 44)

## Device Commands

### Operation Hierarchy

```
Operation (ABC)
├── Command (Operation)
│   ├── SingleCommand (Command)
│   └── BinaryCommand (Command)
│       └── DeviceStatusCommand (BinaryCommand)
└── OperationList (Operation)
```

### Operation (ABC)

Base class for all device operations.

```python
class Operation(ABC):
    @abstractmethod
    def get_status_list(self) -> List[Dict[str, Any]]:
        """Return list of status payloads to send to device."""
```

### Command Classes

#### SingleCommand
Sends `valueSingle` with string values (e.g., status code 80).

```python
class SingleCommand(Command):
    def __init__(self, status_code: str, value: str):
        self.status_code = status_code
        self.value = value
```

#### DeviceStatusCommand
Sends `valueBinary` with F3 status code and 54-char payload.

```python
class DeviceStatusCommand(BinaryCommand):
    @abstractmethod
    def get_header(self) -> str:           # 8-char header

    @abstractmethod
    def get_payload_position(self) -> int:  # Position 0-45

    @abstractmethod
    def get_payload_value(self) -> str:     # Hex value
```

### Built-in Commands

#### PowerOperation
Turns device on or off using both F3 and 80 status codes.

```python
from sharp_devices.device_control import PowerOperation
from sharp_core.states import PowerState

# Turn on
operation = PowerOperation(PowerState.ON)

# Turn off
operation = PowerOperation(PowerState.OFF)
```

Sends:
1. `_PowerStateCommand` (F3): Header `00020000`, position 18
2. `_PowerCommand` (80): Value `30` (ON) or `31` (OFF)

#### ChangeModeCommand
Changes operating mode.

```python
from sharp_devices.device_control import ChangeModeCommand
from sharp_core.states import OperatingMode

command = ChangeModeCommand(OperatingMode.AUTO)
```

- Header: `01000000`
- Position: 0
- Values: From OperatingMode enum

#### HumidificationCommand
Controls humidification feature.

```python
from sharp_devices.device_control import HumidificationCommand
from sharp_core.states import HumidificationState

command = HumidificationCommand(HumidificationState.ON)
```

- Header: `00080000`
- Position: 22
- Values: `00` (OFF), `FF` (ON)

#### ChildLockCommand
Enables/disables child safety lock.

```python
from sharp_devices.device_control import ChildLockCommand
from sharp_core.states import ChildLockState

command = ChildLockCommand(ChildLockState.ON)
```

- Header: `00400000`
- Position: 28
- Values: `00` (OFF), `FF` (ON)

#### LEDBrightnessCommand
Controls LED display brightness.

```python
from sharp_devices.device_control import LEDBrightnessCommand
from sharp_core.states import LEDBrightnessState

command = LEDBrightnessCommand(LEDBrightnessState.AUTO)
```

- Header: `00004000`
- Position: 44
- Values: `00` (OFF), `10` (DIM), `F0` (AUTO)

### Special Operations

#### OperationList
Executes multiple commands in a single API call.

```python
from sharp_devices.device_control import OperationList

commands = [
    HumidificationCommand(HumidificationState.ON),
    LEDBrightnessCommand(LEDBrightnessState.DIM)
]
operation = OperationList(commands)
operations.execute_operation(device, terminal_id, operation)
```

#### RefreshStateOperation
Refreshes device state without sending commands.

```python
from sharp_devices.device_control import RefreshStateOperation

operation = RefreshStateOperation()
operations.execute_operation(device, terminal_id, operation)
```

## Command Execution Flow

1. **Submit Command**:
   ```
   POST /control/deviceControl
   Body: {controlList: [{deviceId, echonetNode, echonetObject, status: [...]}]}
   Response: {controlList: [{id: "operation-id"}]}
   ```

2. **Poll Status** (10 attempts, 1 second intervals):
   ```
   POST /control/controlResult
   Body: {resultList: [{id: "operation-id"}]}
   Response: {resultList: [{status, errorCode, epc, edt}]}
   ```

3. **Success Conditions**:
   - `status == "success"` or `status == "unmatch"`
   - `errorCode == null`

4. **Failure Conditions**:
   - `status == "error"`
   - Timeout after 10 attempts

## API Endpoints

All endpoints use base URL: `https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/`

### Authentication
- `POST /setting/login/` - Login with terminal ID

### Device Discovery
- `GET /setting/boxInfo?mode=other` - Get device list

### Device Pairing
- `POST /setting/pairing/?boxId={boxId}&houseFlag=false` - Pair device

### Device Control
- `GET /control/deviceProperty` - Get device properties
- `POST /control/deviceControl` - Submit commands
- `POST /control/controlResult` - Check command status

## Error Handling

```python
# Operations return False on failure
if not operations.setup_with_terminal_id(terminal_id):
    print("Setup failed")

# Exceptions raised for HTTP errors
try:
    properties = operations.get_device_properties(device)
except requests.HTTPError as e:
    print(f"API error: {e}")
```

## Dependencies

- `sharp-core`: HTTP client and state enumerations

## Usage Examples

### Complete Device Control

```python
from sharp_core import SharpClient
from sharp_core.states import *
from sharp_devices.operations import SharpOperations
from sharp_devices.device_control import *

# Initialize
client = SharpClient()
ops = SharpOperations(client)

# Authenticate and discover
terminal_id = "your-terminal-id"
ops.setup_with_terminal_id(terminal_id)
devices = ops.discover_and_pair_devices(terminal_id)

# Control first device
device = devices[0]

# Turn on and set to auto mode
ops.execute_operation(device, terminal_id, PowerOperation(PowerState.ON))
ops.execute_operation(device, terminal_id, ChangeModeCommand(OperatingMode.AUTO))

# Enable humidification with dim LED
commands = [
    HumidificationCommand(HumidificationState.ON),
    LEDBrightnessCommand(LEDBrightnessState.DIM)
]
ops.execute_operation(device, terminal_id, OperationList(commands))

# Read current state
props = ops.get_device_properties(device)
print(f"Temperature: {props.f1_property.temperature}°C")
print(f"Humidity: {props.f1_property.humidity}%")
print(f"Mode: {props.f3_property.operating_mode.name}")
print(f"Power: {props.f3_property.power.name}")
```

### Custom Command

```python
from sharp_devices.device_control import DeviceStatusCommand

class CustomCommand(DeviceStatusCommand):
    def __init__(self, value: str):
        super().__init__()
        self.value = value

    def get_header(self) -> str:
        return "01000000"  # Your header

    def get_payload_position(self) -> int:
        return 10  # Your position

    def get_payload_value(self) -> str:
        return self.value

# Use custom command
command = CustomCommand("FF")
operations.execute_operation(device, terminal_id, command)
```

## Development

```bash
# Install workspace
uv sync

# Test imports
uv run python -c "from sharp_devices import SharpOperations; print('Success')"

# Run with CLI
uv run sharp-cli <terminal-id>
```

## License

Part of the Sharp IoT device control workspace. Sharp IoT is a trademark of Sharp Corporation.
