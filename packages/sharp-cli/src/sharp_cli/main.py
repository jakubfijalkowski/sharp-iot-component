import sys
from sharp_core import SharpClient
from sharp_core.states import *
from sharp_devices.operations import SharpOperations
from sharp_devices.device_control import ChangeModeCommand, ChildLockCommand, HumidificationCommand, LEDBrightnessCommand, PowerOperation, RefreshStateOperation


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <terminalAppId>")
        print()
        print("To get a terminal ID, run the authentication server:")
        print("  uv run python sharp_auth/auth_server.py")
        print("Then complete the authentication process in your browser.")
        return 1

    # Get terminal ID from command line
    terminal_app_id = sys.argv[1]
    print(f"Using terminalAppId: {terminal_app_id}")

    # Initialize client and operations
    client = SharpClient()
    operations = SharpOperations(client)

    # Setup with terminal ID
    if not operations.setup_with_terminal_id(terminal_app_id):
        print("Error: Setup with terminal ID failed")
        return 1

    # Discover and pair devices
    box_infos = operations.discover_and_pair_devices(terminal_app_id)

    operations.execute_operation(box_infos[0], terminal_app_id, RefreshStateOperation())

    # Get device properties for each box
    print("\nDevice Properties:")
    for box_info in box_infos:
        if box_info.echonet_node and box_info.echonet_object:
            print(f"\nProperties for box {box_info.box_id}:")
            properties = operations.get_device_properties(box_info)
            print(properties)

    return 0

if __name__ == "__main__":
    sys.exit(main())
