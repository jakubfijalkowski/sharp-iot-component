from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List

from sharp_core.states import OperatingMode, HumidificationState, LEDBrightnessState, ChildLockState, PowerState

class Operation(ABC):
    """
    Base class for all device operations.

    An operation represents a logical unit of work that can be executed on a device.
    It encapsulates the logic for building the status list that gets sent to the API.
    """

    @abstractmethod
    def get_status_list(self) -> List[Dict[str, Any]]:
        """
        Get the status list for this operation.

        The status list contains the complete status payloads that will be sent
        to the device control API.

        Returns:
            List[Dict[str, Any]]: List of status payloads
        """
        pass

class Command(Operation):
    """
    Base class for all device commands.

    A command is also an operation that executes a single command.
    """

    @abstractmethod
    def get_status_payload(self) -> Dict[str, Any]:
        """
        Get the complete status payload for this command.

        Returns:
            dict: Complete status structure like:
            {
                "statusCode": "F3",
                "valueType": "valueBinary",
                "valueBinary": {"code": "010000000000..."}
            }
            or
            {
                "statusCode": "80",
                "valueType": "valueSingle",
                "valueSingle": {"code": "25"}
            }
        """
        pass

    def get_status_list(self) -> List[Dict[str, Any]]:
        """
        Get the status list for this command operation.

        For a single command, this returns a list containing just this command's status payload.

        Returns:
            List[Dict[str, Any]]: List containing this command's status payload
        """
        return [self.get_status_payload()]


class SingleCommand(Command):
    """
    Command that sends valueSingle with string values.
    """

    def __init__(self, status_code: str, value: str):
        """
        Initialize the singular command.

        Args:
            status_code: The statusCode (e.g., "80")
            value: The string value to send
        """
        self.status_code = status_code
        self.value = value

    def get_status_payload(self) -> Dict[str, Any]:
        """
        Get the complete status payload for this singular command.

        Returns:
            dict: Complete status structure for valueSingle
        """
        return {
            "statusCode": self.status_code,
            "valueType": "valueSingle",
            "valueSingle": {"code": self.value}
        }

class BinaryCommand(Command):
    """
    Base class for commands that send valueBinary type.
    """

    @abstractmethod
    def get_status_code(self) -> str:
        """
        Get the statusCode for this binary command.

        Returns:
            str: statusCode string (e.g., "F3")
        """
        pass

    @abstractmethod
    def get_binary_payload(self) -> str:
        """
        Get the binary payload for this command.

        Returns:
            str: Binary payload string
        """
        pass

    def get_status_payload(self) -> Dict[str, Any]:
        """
        Get the complete status payload for this binary command.

        Returns:
            dict: Complete status structure for valueBinary
        """
        return {
            "statusCode": self.get_status_code(),
            "valueType": "valueBinary",
            "valueBinary": {"code": self.get_binary_payload()}
        }


class DeviceStatusCommand(BinaryCommand):
    """
    Base class for device status control commands.

    Device status is controlled by setting the F3 property with a payload consisting of:
    - 8 characters header (describes the property being changed)
    - 46 characters payload (commands at specific positions, rest filled with '0')

    Total payload length: 54 characters
    """

    def __init__(self):
        """
        Initialize the command.
        """
        pass

    def get_status_code(self) -> str:
        """
        Get the statusCode for device status commands.
        All device status commands use the F3 statusCode.

        Returns:
            str: "F3"
        """
        return "F3"

    @abstractmethod
    def get_header(self) -> str:
        """
        Get the 8-character header that describes the property being changed.

        Returns:
            str: 8-character header string
        """
        pass

    @abstractmethod
    def get_payload_position(self) -> int:
        """
        Get the position in the payload where this command's data should be placed.

        Returns:
            int: Position (0-45) in the 46-character payload
        """
        pass

    @abstractmethod
    def get_payload_value(self) -> str:
        """
        Get the hex string value for this command.

        Returns:
            str: Hex string value to place at the command's position
        """
        pass

    def build_payload(self) -> str:
        """
        Get the complete payload that would be sent to the device.
        Useful for debugging and testing.

        Returns:
            str: Complete 54-character payload
        """
        header = self.get_header()
        if len(header) != 8:
            raise ValueError(f"Header must be exactly 8 characters, got {len(header)}")

        # Initialize 46-character payload with zeros
        payload_chars = ['0'] * 46

        # Set command data at the specific position
        position = self.get_payload_position()
        value = self.get_payload_value()

        if position < 0 or position >= 46:
            raise ValueError(f"Payload position must be between 0 and 45, got {position}")

        # Ensure value fits in the available space
        if position + len(value) > 46:
            raise ValueError(f"Value at position {position} exceeds payload boundary")

        # Set the value at the specified position
        for i, char in enumerate(value):
            payload_chars[position + i] = char

        payload = ''.join(payload_chars)
        return header + payload

    def get_binary_payload(self) -> str:
        """
        Get the binary payload for device status commands.
        Uses the structured 54-character format.

        Returns:
            str: Complete 54-character payload
        """
        return self.build_payload()

class OperationList(Operation):
    """
    Concrete operation that wraps a list of commands.

    This is the most common type of operation - simply executing
    a list of commands in sequence.
    """

    def __init__(self, commands: List['Command']):
        """
        Initialize the operation with a list of commands.

        Args:
            commands: List of commands to execute
        """
        if not commands:
            raise ValueError("OperationList must contain at least one command")
        self.commands = commands

    def get_status_list(self) -> List[Dict[str, Any]]:
        """
        Get the status list for this operation by converting commands to status payloads.

        Returns:
            List[Dict[str, Any]]: List of status payloads from all commands
        """
        return [command.get_status_payload() for command in self.commands]


class ChangeModeCommand(DeviceStatusCommand):
    """
    Command to change the operating mode of the device.
    """

    def __init__(self, mode: OperatingMode):
        super().__init__()
        self.mode = mode

    def get_header(self) -> str:
        return "01000000"

    def get_payload_position(self) -> int:
        return 0

    def get_payload_value(self) -> str:
        return self.mode.value


class HumidificationCommand(DeviceStatusCommand):
    """
    Command to control the humidification state of the device.
    """

    def __init__(self, state: HumidificationState):
        super().__init__()
        self.state = state

    def get_header(self) -> str:
        return "00080000"

    def get_payload_position(self) -> int:
        return 22

    def get_payload_value(self) -> str:
        return self.state.value


class LEDBrightnessCommand(DeviceStatusCommand):
    """
    Command to control the LED brightness of the device.
    """

    def __init__(self, state: LEDBrightnessState):
        super().__init__()
        self.state = state

    def get_header(self) -> str:
        return "00004000"

    def get_payload_position(self) -> int:
        return 44

    def get_payload_value(self) -> str:
        return self.state.value


class ChildLockCommand(DeviceStatusCommand):
    """
    Command to control the child lock state of the device.
    """

    def __init__(self, state: ChildLockState):
        super().__init__()
        self.state = state

    def get_header(self) -> str:
        return "00400000"

    def get_payload_position(self) -> int:
        return 28

    def get_payload_value(self) -> str:
        return self.state.value


class _PowerStateCommand(DeviceStatusCommand):
    """
    Command to control the power state of the device.
    """

    def __init__(self, state: PowerState):
        super().__init__()
        self.state = state

    def get_header(self) -> str:
        return "00020000"

    def get_payload_position(self) -> int:
        return 18

    def get_payload_value(self) -> str:
        return self.state.value

class _PowerCommand(SingleCommand):
    """
    Command to control the power state of the device using status code 80.
    """

    def __init__(self, state: PowerState):
        """
        Initialize the power command.

        Args:
            state: PowerState enum value (ON or OFF)
        """
        value = "30" if state == PowerState.ON else "31"
        super().__init__("80", value)

class PowerOperation(OperationList):
    """
    Operation that turns the device on or off using both power commands.
    This ensures the device state is properly synchronized.
    """

    def __init__(self, state: PowerState):
        """
        Initialize the power operation.

        Args:
            state: PowerState enum value (ON or OFF)
        """
        super().__init__([
            _PowerStateCommand(state),
            _PowerCommand(state)
        ])

class RefreshStateOperation(Operation):
    """
    Operation that sends an empty list to refresh the device state.
    """

    def get_status_list(self) -> List[Dict[str, Any]]:
        return []


