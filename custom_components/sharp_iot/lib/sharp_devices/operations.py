from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time
import logging
from ..sharp_core import SharpClient
from .device_control import DeviceStatusCommand, Command, Operation, OperationList
from .device_properties import DeviceProperties

logger = logging.getLogger(__name__)

@dataclass
class BoxInfo:
    """Class to hold box information including boxId, echonetNode, and echonetObject."""
    box_id: str
    echonet_node: str
    echonet_object: str
    deviceId: str
    terminals: List[str]

    def __str__(self):
        return f"Box {self.box_id} @ {self.echonet_node} at {self.echonet_object} with deviceId {self.deviceId} and terminals {self.terminals}"

class SharpOperations:
    def __init__(self, client: SharpClient):
        self.client = client

    def setup_with_terminal_id(self, terminal_app_id: str) -> bool:
        """Setup operations with existing terminal app ID."""
        try:
            url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/login/"
            params = {
                "serviceName": "sharp-eu"
            }
            data = {
                "terminalAppId": terminal_app_id
            }
            self.client.post_json(url, params=params, json=data)
            return True
        except Exception as e:
            logger.error(f"Failed to setup operations with terminal ID '{terminal_app_id}': {e}")
            return False

    def discover_and_pair_devices(self, terminal_app_id: str) -> List[BoxInfo]:
        """Discover devices and pair any unpaired ones."""
        # Get box information
        box_infos = self._get_box_ids(terminal_app_id)

        # Pair unpaired devices
        logger.info("Starting device pairing process for unpaired devices")
        for box_info in box_infos:
            if terminal_app_id not in box_info.terminals:
                logger.info(f"Pairing device with box_id: {box_info.box_id}")
                self._pair_device(box_info.box_id)

        return box_infos

    def get_device_properties(self, box_info: BoxInfo) -> DeviceProperties:
        """Get device properties for a specific box."""
        url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/control/deviceProperty"
        params = {
            "boxId": box_info.box_id,
            "echonetNode": box_info.echonet_node,
            "echonetObject": box_info.echonet_object,
            "status": "true"
        }
        response = self.client.get_json(url, params=params)
        return DeviceProperties.from_api_response(response)

    def execute_operation(self, box_info: BoxInfo, terminal_app_id: str, operation: Operation) -> bool:
        """Execute an operation on a device."""
        # First, make the control request
        control_url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/control/deviceControl"
        control_params = {
            "terminalAppId": terminal_app_id,
            "boxId": box_info.box_id
        }

        # Get status list directly from the operation
        status_list = operation.get_status_list()

        control_data = {
            "controlList": [
                {
                    "deviceId": box_info.deviceId,
                    "echonetNode": box_info.echonet_node,
                    "echonetObject": box_info.echonet_object,
                    "status": status_list
                }
            ]
        }

        try:
            control_result = self.client.post_json(control_url, params=control_params, json=control_data)

            if not control_result.get("controlList") or not control_result["controlList"][0].get("id"):
                logger.error(f"No operation ID received for device control on box_id: {box_info.box_id}")
                return False

            operation_id = control_result["controlList"][0]["id"]
            logger.info(f"Control request sent for box_id: {box_info.box_id}, operation_id: {operation_id}")

            # Now check the status 10 times
            status_url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/control/controlResult"
            status_params = {
                "boxId": box_info.box_id
            }
            status_data = {
                "resultList": [
                    {
                        "id": operation_id
                    }
                ]
            }

            for i in range(10):
                time.sleep(1)  # Wait 1s between checks
                status_result = self.client.post_json(status_url, params=status_params, json=status_data)

                if not status_result.get("resultList"):
                    logger.debug(f"Status check {i+1}/10: No status result received for operation_id: {operation_id}")
                    continue

                result = status_result["resultList"][0]
                logger.debug(f"Status check {i+1}/10 for operation_id {operation_id}: Status: {result.get('status')}, Error: {result.get('errorCode')}")

                if result.get("status") == "error":
                    logger.error(f"Operation {operation_id} failed with error code: {result.get('errorCode')}")
                    return False
                elif result.get("errorCode") is None and result.get("status") in ["unmatch", "success"]:
                    logger.info(f"Operation {operation_id} completed successfully: epc={result.get('epc')}, edt={result.get('edt')}")
                    return True

            logger.info(f"Operation {operation_id} status checks completed without success after 10 attempts")
            return False

        except Exception as e:
            logger.error(f"Error during device control for box_id {box_info.box_id}: {e}")
            return False

    def execute_commands(self, box_info: BoxInfo, terminal_app_id: str, commands: List[Command]) -> bool:
        """Execute multiple commands in a single deviceControl call (backward compatibility wrapper)."""
        operation = OperationList(commands)
        return self.execute_operation(box_info, terminal_app_id, operation)

    def _get_box_ids(self, terminal_app_id: str) -> List[BoxInfo]:
        """Make an API call to get box info and extract box information."""
        url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/boxInfo"
        params = {
            "mode": "other"
        }

        box_info = self.client.get_json(url, params=params)
        box_infos = []

        for box in box_info['box']:
            echonet_data = box['echonetData'][0]  # Take first device
            echonet_node = echonet_data.get('echonetNode')
            echonet_object = echonet_data.get('echonetObject')
            deviceId = echonet_data.get('deviceId')

            terminal_app_infos = box['terminalAppInfo']
            terminals = [info['terminalAppId'] for info in terminal_app_infos]

            box_infos.append(BoxInfo(
                box_id=box['boxId'],
                echonet_node=echonet_node,
                echonet_object=echonet_object,
                deviceId=deviceId,
                terminals=terminals
            ))
        return box_infos

    def _pair_device(self, box_id: str) -> None:
        """Pair a device with the current terminal."""
        url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/pairing/"
        params = {
            "boxId": box_id,
            "houseFlag": "false"
        }
        self.client.post_json(url, params=params)