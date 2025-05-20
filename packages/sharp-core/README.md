# Sharp Core

Core HTTP client and shared utilities for Sharp IoT device communication.

## Overview

`sharp-core` provides the foundation for all Sharp IoT device interactions, including:
- HTTP client with automatic authentication headers
- Device state enumerations
- Protocol constants

This package is used by all other Sharp IoT packages and should not be used directly by end users.

## Components

### SharpClient

HTTP client wrapper that handles all API communication with Sharp's cloud services.

**Features:**
- Automatic `appSecret` injection on all requests
- User-Agent mimicking Android app for EU region
- Request/response error handling with `raise_for_status()`
- JSON parsing with detailed error messages

**Example:**
```python
from sharp_core import SharpClient

client = SharpClient()

# GET request
response = client.get_json("https://api.example.com/endpoint", params={"key": "value"})

# POST request
response = client.post_json("https://api.example.com/endpoint", json={"data": "value"})
```

### State Enumerations

All device states are defined as enums with hex string values:

#### PowerState
```python
class PowerState(Enum):
    OFF = "00"
    ON = "FF"
```

#### OperatingMode
```python
class OperatingMode(Enum):
    OFF = "00"        # When device is powered off
    LOW = "14"
    MED = "15"
    MAX = "16"
    AUTO = "10"
    POLLEN = "13"
    ION_SHOWER = "40"
    SLEEP = "11"
    SHARP_LIFE_AIR = "20"
```

#### HumidificationState
```python
class HumidificationState(Enum):
    OFF = "00"
    ON = "FF"
```

#### ChildLockState
```python
class ChildLockState(Enum):
    OFF = "00"
    ON = "FF"
```

#### LEDBrightnessState
```python
class LEDBrightnessState(Enum):
    OFF = "00"
    DIM = "10"
    AUTO = "F0"
```

#### QualityLevel
```python
class QualityLevel(Enum):
    CLEAN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

    @classmethod
    def parse(cls, int_value: int) -> 'QualityLevel':
        """Parse sensor reading into quality level."""
```

Parsing logic:
- `> 75`: VERY_HIGH
- `56-75`: HIGH
- `36-55`: MEDIUM
- `16-35`: LOW
- `< 16`: CLEAN

#### WaterContainerState
```python
class WaterContainerState(Enum):
    UNKNOWN = 0
    FULL = 1
    EMPTY = 2

    @classmethod
    def parse(cls, int_value: int) -> 'WaterContainerState':
        """Parse sensor reading into container state."""
```

## Constants

### API Configuration

```python
APP_SECRET = "pngtfljRoYsJE9NW7opn1t2cXA5MtZDKbwon368hs80="
USER_AGENT = "smartlink_v200a_eu Dalvik/2.1.0 (Linux; U; Android 15; SM-S918B Build/AP3A.240905.015.A2)"
```

### API Endpoints

- **HMS API Base**: `https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/`
- **Auth Server**: `https://auth-eu.global.sharp/oxauth/restv1/`

## Dependencies

- `requests>=2.31.0`: HTTP client library

## Usage in Other Packages

All Sharp IoT packages depend on `sharp-core`:

```python
# In sharp-devices
from sharp_core import SharpClient
from sharp_core.states import PowerState, OperatingMode

# In sharp-auth
from sharp_core import SharpClient

# In sharp-homeassistant
from sharp_core.states import PowerState, QualityLevel, WaterContainerState
```

## Development

This package is part of the Sharp IoT workspace:

```bash
# Install workspace dependencies
uv sync

# Test imports
uv run python -c "from sharp_core import SharpClient; from sharp_core.states import *; print('Import successful')"
```

## Protocol Details

### Request Format

All API requests include:
- `appSecret` query parameter (automatically injected by SharpClient)
- `User-Agent` header mimicking Android app
- `Accept: application/json` header (GET requests)
- `Content-Type: application/json; charset=utf-8` header (POST requests)

### Response Handling

- Successful responses return JSON data
- Failed requests raise `requests.HTTPError` via `raise_for_status()`
- JSON parsing errors include detailed debugging information

## License

Part of the Sharp IoT device control workspace. Sharp IoT is a trademark of Sharp Corporation.
