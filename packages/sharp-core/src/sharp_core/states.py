from enum import Enum

class PowerState(Enum):
    """Enumeration of available power states for the device."""
    OFF = "00"
    ON = "FF"

class OperatingMode(Enum):
    """Enumeration of available operating modes for the device."""
    OFF = "00"  # When device is powered off
    LOW = "14"
    MED = "15"
    MAX = "16"
    AUTO = "10"
    POLLEN = "13"
    ION_SHOWER = "40"
    SLEEP = "11"
    SHARP_LIFE_AIR = "20"

class HumidificationState(Enum):
    """Enumeration of available humidification states for the device."""
    OFF = "00"
    ON = "FF"

class LEDBrightnessState(Enum):
    """Enumeration of available LED brightness states for the device."""
    OFF = "00"
    DIM = "10"
    AUTO = "F0"

class ChildLockState(Enum):
    """Enumeration of available child lock states for the device."""
    OFF = "00"
    ON = "FF"

class QualityLevel(Enum):
    """Enumeration of air quality levels based on sensor readings."""
    CLEAN = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

    @classmethod
    def parse(cls, int_value: int) -> 'QualityLevel':
        """Parse a sensor reading into an air quality level."""
        if int_value > 75:
            return cls.VERY_HIGH
        elif 56 <= int_value <= 75:
            return cls.HIGH
        elif 36 <= int_value < 56:
            return cls.MEDIUM
        elif 16 <= int_value < 36:
            return cls.LOW
        else:
            return cls.CLEAN

class WaterContainerState(Enum):
    """Enumeration of water container states for the device."""
    UNKNOWN = 0
    FULL = 1
    EMPTY = 2

    @classmethod
    def parse(cls, int_value: int) -> 'WaterContainerState':
        """Parse a sensor reading into a water container state."""
        if int_value == 0:
            return cls.UNKNOWN
        elif int_value == 1:
            return cls.FULL
        elif int_value == 2:
            return cls.EMPTY
        else:
            return cls.UNKNOWN
