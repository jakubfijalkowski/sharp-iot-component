from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from sharp_core.states import OperatingMode, HumidificationState, LEDBrightnessState, ChildLockState, PowerState, QualityLevel, WaterContainerState


@dataclass
class F1Property:
    temperature: int
    humidity: int
    pm25_level: int

    @classmethod
    def from_hex(cls, hex_string: str) -> 'F1Property':
        # Remove any whitespace
        hex_string = hex_string.strip()

        # Convert hex string to bytes for easier slicing
        data = bytes.fromhex(hex_string)

        return cls(
            temperature=int.from_bytes(data[3:4], 'big'),
            humidity=int.from_bytes(data[4:5], 'big'),
            pm25_level=int.from_bytes(data[28:30], 'little')
        )

    def __str__(self) -> str:
        return f"F1(temp={self.temperature}°C, hum={self.humidity}%, pm25={self.pm25_level})"

@dataclass
class F2Property:
    air_quality: QualityLevel
    dust_level: QualityLevel
    odor_level: QualityLevel
    water_container: WaterContainerState

    @classmethod
    def from_hex(cls, hex_string: str) -> 'F2Property':
        # Remove any whitespace
        hex_string = hex_string.strip()

        # Convert hex string to bytes for easier slicing
        data = bytes.fromhex(hex_string)

        return cls(
            odor_level=QualityLevel.parse(int.from_bytes(data[14:15], 'big')),
            dust_level=QualityLevel.parse(int.from_bytes(data[15:16], 'big')),
            air_quality=QualityLevel.parse(int.from_bytes(data[17:18], 'big')),
            water_container=WaterContainerState.parse(int.from_bytes(data[18:19], 'big'))
        )

    def __str__(self) -> str:
        return f"F2(air={self.air_quality.name}, dust={self.dust_level.name}, odor={self.odor_level.name}, water={self.water_container.name})"

@dataclass
class F3Property:
    """
    Represents the F3 property state of the device.
    The positions of each state match the positions used in the command classes.
    """
    operating_mode: OperatingMode
    humidification: HumidificationState
    power: PowerState
    child_lock: ChildLockState
    led_brightness: LEDBrightnessState

    @classmethod
    def from_hex(cls, hex_string: str) -> 'F3Property':
        """
        Parse the F3 property hex string into device states.

        Args:
            hex_string: The hex string from the device (should be 54 characters)

        Returns:
            F3Property instance with parsed states
        """
        # Remove any whitespace
        hex_string = hex_string.strip()

        # Skip the 8-character header and get the 46-character payload
        if len(hex_string) != 54:
            raise ValueError(f"F3 property must be 54 characters long, got {len(hex_string)}")

        payload = hex_string[8:]  # Skip header

        # Parse each state based on the positions defined in the command classes
        return cls(
            operating_mode=OperatingMode(payload[0:2]),  # Position 0
            humidification=HumidificationState(payload[22:24]),  # Position 22
            power=PowerState(payload[18:20]),  # Position 18
            child_lock=ChildLockState(payload[28:30]),  # Position 30
            led_brightness=LEDBrightnessState(payload[44:46])  # Position 44
        )

    def __str__(self) -> str:
        return f"F3(mode={self.operating_mode.name}, hum={self.humidification.name}, pwr={self.power.name}, lock={self.child_lock.name}, led={self.led_brightness.name})"

@dataclass
class DeviceProperties:
    echonet_node: str
    label: str
    f1_property: Optional[F1Property] = None
    f2_property: Optional[F2Property] = None
    f3_property: Optional[F3Property] = None

    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'DeviceProperties':
        """Create a DeviceProperties instance from API response data."""
        # Get the device property data from the nested structure
        device_property = response_data.get('deviceProperty', {})

        # Extract basic properties
        echonet_node = device_property.get('echonetNode', '')
        label = device_property.get('label', '')

        # Extract and decode F1, F2, and F3 properties if present
        f1_property = None
        f2_property = None
        f3_property = None
        status_list = device_property.get('status', [])
        for status in status_list:
            status_code = status.get('statusCode', '').lower()
            if status_code == 'f1':
                f1_property = F1Property.from_hex(status.get('valueBinary', {}).get('code', ''))
            elif status_code == 'f2':
                f2_property = F2Property.from_hex(status.get('valueBinary', {}).get('code', ''))
            elif status_code == 'f3':
                f3_property = F3Property.from_hex(status.get('valueBinary', {}).get('code', ''))

        return cls(
            echonet_node=echonet_node,
            label=label,
            f1_property=f1_property,
            f2_property=f2_property,
            f3_property=f3_property
        )

    def __str__(self) -> str:
        """String representation of the device properties."""
        return f"{self.label} ({self.echonet_node})"

    def debug_str(self) -> str:
        """Detailed string representation for debugging."""
        result = [
            f"Echonet Node: {self.echonet_node}",
            f"Label: {self.label}"
        ]

        if self.f1_property:
            result.append("\nF1 Property:")
            result.append("\n".join(
                f"{field:20}: {getattr(self.f1_property, field)}"
                for field in self.f1_property.__dataclass_fields__
            ))

        if self.f2_property:
            result.append("\nF2 Property:")
            result.append("\n".join(
                f"{field:20}: {getattr(self.f2_property, field)}"
                for field in self.f2_property.__dataclass_fields__
            ))

        if self.f3_property:
            result.append("\nF3 Property:")
            result.append("\n".join(
                f"{field:20}: {getattr(self.f3_property, field).name}"
                for field in self.f3_property.__dataclass_fields__
            ))

        return "\n".join(result)
