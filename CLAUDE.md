# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run authentication server**: `uv run sharp-auth` (starts FastAPI auth server at <http://localhost:8000>)
- **Run device CLI**: `uv run sharp-cli <terminalAppId>` (control devices with existing terminal ID)
- **Install dependencies**: `uv sync` (required - always use uv, never pip)
- **Python version**: Requires Python 3.13+ (see .python-version)
- **Test terminal ID**: (ask user to provide it)
- **Home Assistant Integration**: Copy `packages/sharp-homeassistant/src/custom_components/sharp_iot/` to your HA `custom_components/` directory

**IMPORTANT**: Always use `uv run` prefix for all Python commands. Never run Python directly or use pip.

## Architecture Overview

This is a Sharp IoT device client for controlling air purifiers via their cloud API. The codebase implements a reverse-engineered protocol combining OAuth 2.0 authentication with EchoNet Lite device communication. It provides three interfaces: CLI tool, FastAPI auth server, and Home Assistant integration.

### Core Architecture

**uv Workspace Structure**: This project uses uv workspaces with the following packages:

**Packages**:

- `sharp-core`: HTTP client and shared utilities (`client.py`, `states.py`)
- `sharp-auth`: FastAPI authentication server (`auth_server.py` with Jinja2 templates)
- `sharp-devices`: Device operations and control (`operations.py`, `device_control.py`, `device_properties.py`)
- `sharp-cli`: Command-line interface (`main.py`)
- `sharp-homeassistant`: Home Assistant custom component (`custom_components/sharp_iot/`)

**Entry Points**:

- `sharp-auth`: FastAPI server for OAuth 2.0 authentication at <http://localhost:8000>
- `sharp-cli <terminalAppId>`: Device control CLI with existing terminal session
- Home Assistant integration: Configured via UI, requires terminal ID from auth server

### Protocol Flow

**Two-Phase Architecture:**

**Phase 1 - Authentication** (sharp-auth package):

- FastAPI server provides web UI for OAuth 2.0 flow
- OAuth 2.0 with Sharp's EU auth server, requires manual callback URL copying due to mobile app redirect scheme (`sharp-cocoroair-eu://authorize`)
- Terminal registration: Creates unique terminal session with random 5-char name
- Returns terminalAppId for Phase 2 (used by CLI and Home Assistant)

**Phase 2 - Operations** (sharp-devices package):

- Setup with terminal ID (required for both CLI and Home Assistant)
- Device discovery: Retrieves box/gateway information and pairs unpaired devices
- Command execution: Two-phase async process - submit commands, then poll 10 times (1s intervals) for completion status
- State reading: Parse hex-encoded device properties (F1=environmental, F2=sensors, F3=control state)

### Home Assistant Integration

**Platforms Provided**:

- **Fan**: Operating mode control (auto, sleep, low, medium, max, pollen, ion_shower, sharp_life_air) - unavailable when power is OFF
- **Sensors**: Temperature, humidity, PM2.5, air quality, dust level, odor level - unavailable when power is OFF
- **Switches**: Power, humidification, child lock, LED brightness - power switch always available, others unavailable when power is OFF
- **Binary Sensors**: Water level (problem state when empty) - unavailable when power is OFF

**Data Update Coordinator**:

- Polls devices every 30 seconds (configurable via `UPDATE_INTERVAL`)
- Handles device discovery on first run
- Executes commands asynchronously via executor job
- Automatically refreshes after command execution

**Configuration Flow**:

- UI-based configuration via config flow
- Validates terminal ID by testing connection and device discovery
- Single entry per terminal ID (enforced via unique_id)

### Key Constants

- **App Secret**: `pngtfljRoYsJE9NW7opn1t2cXA5MtZDKbwon368hs80=` (required on all API calls)
- **User Agent**: Mimics Android app for EU region (`smartlink_v200a_eu Dalvik/2.1.0 (Linux; U; Android 15; SM-S918B Build/AP3A.240905.015.A2)`)
- **API Base**: `https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/`
- **Auth Server**: `https://auth-eu.global.sharp/oxauth/restv1/`

### Data Model

**Hierarchy**: Terminal → Box (Gateway) → Device → Properties

- **F1 Property**: Environmental data (temperature °C, humidity %, PM2.5 μg/m³)
- **F2 Property**: Quality sensors (odor, dust, air quality as QualityLevel enum, water container state)
- **F3 Property**: Device control state (54-char hex: 8-char header + 46-char payload)

**Property Parsing**:

- F1: Bytes at positions 3-4 (temp, humidity), 28-30 (PM2.5 little-endian)
- F2: Bytes at positions 14-15 (odor, dust), 17-18 (air quality), 18-19 (water container)
- F3: Payload positions match command positions (mode@0, power@18, humidification@22, child_lock@28, LED@44)

### Command Structure

**Operation Hierarchy**:

- `Operation` (ABC): Base class with `get_status_list()` method
- `Command` (Operation): Single command with `get_status_payload()` method
  - `SingleCommand`: Status code 80 with `valueSingle` (e.g., power: "30"=ON, "31"=OFF)
  - `BinaryCommand`: Status code F3 with `valueBinary`
    - `DeviceStatusCommand`: F3 commands with structured 54-char payload
- `OperationList` (Operation): Wraps list of commands for batch execution
- `PowerOperation` (OperationList): Sends both `_PowerStateCommand` (F3) and `_PowerCommand` (80) for state synchronization

**Device Status Commands** (all use F3 statusCode):

- `ChangeModeCommand`: Header `01000000`, position 0, value from `OperatingMode` enum
- `PowerStateCommand`: Header `00020000`, position 18, value from `PowerState` enum
- `HumidificationCommand`: Header `00080000`, position 22, value from `HumidificationState` enum
- `ChildLockCommand`: Header `00400000`, position 28, value from `ChildLockState` enum
- `LEDBrightnessCommand`: Header `00004000`, position 44, value from `LEDBrightnessState` enum

**Special Operations**:

- `RefreshStateOperation`: Sends empty status list to refresh device state without making changes

### State Enums

All states are defined in `sharp_core.states`:

- `PowerState`: OFF="00", ON="FF"
- `OperatingMode`: OFF="00", LOW="14", MED="15", MAX="16", AUTO="10", POLLEN="13", ION_SHOWER="40", SLEEP="11", SHARP_LIFE_AIR="20"
- `HumidificationState`: OFF="00", ON="FF"
- `ChildLockState`: OFF="00", ON="FF"
- `LEDBrightnessState`: OFF="00", DIM="10", AUTO="F0"
- `QualityLevel`: CLEAN=0, LOW=1, MEDIUM=2, HIGH=3, VERY_HIGH=4 (parsed from sensor int values)
- `WaterContainerState`: UNKNOWN=0, FULL=1, EMPTY=2 (parsed from sensor int values)

## Code Conventions

- **Type hints**: Use typing module extensively (`Dict[str, Any]`, `Optional[str]`, `List[BoxInfo]`)
- **Dataclasses**: Use `@dataclass` for structured data (`BoxInfo`, `F1Property`, `F2Property`, `F3Property`, `DeviceProperties`)
- **Error handling**: `raise_for_status()` for HTTP errors, optional returns for missing data
- **Constants**: Module-level constants in UPPER_CASE
- **Import order**: Standard library, third-party, local modules
- **Async patterns**: Home Assistant uses `hass.async_add_executor_job()` for sync Sharp API calls
- **Logging**: Use module-level logger `_LOGGER = logging.getLogger(__name__)`
