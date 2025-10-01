import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

USER_AGENT = "smartlink_v200a_eu Dalvik/2.1.0 (Linux; U; Android 15; SM-S918B Build/AP3A.240905.015.A2)"
APP_SECRET = "pngtfljRoYsJE9NW7opn1t2cXA5MtZDKbwon368hs80="

class SharpClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a GET request with proper headers and error handling."""
        if params is None:
            params = {}
        if headers is None:
            headers = {}

        # Always include app secret in params
        params["appSecret"] = APP_SECRET

        # Set default headers if not provided
        if "Accept" not in headers:
            headers["Accept"] = "application/json"

        response = self.session.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response

    def post(self, url: str, params: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a POST request with proper headers and error handling."""
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        if json is None:
            json = {}

        # Always include app secret in params
        params["appSecret"] = APP_SECRET

        # Set default headers if not provided
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if "Accept" not in headers:
            headers["Accept"] = "application/json"

        response = self.session.post(url, params=params, headers=headers, json=json)
        response.raise_for_status()
        return response

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request and return the JSON response."""
        response = self.get(url, params, headers)
        return response.json()

    def post_json(self, url: str, params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request and return the JSON response."""
        response = self.post(url, params, headers, json)
        try:
            return response.json()
        except ValueError as e:
            # Better error details for JSON parsing issues
            logger.error(f"JSON Parse Error for URL: {url}")
            logger.error(f"Status Code: {response.status_code}")
            logger.error(f"Response Headers: {dict(response.headers)}")
            logger.error(f"Response Text: {response.text[:500]}...")
            raise ValueError(f"Failed to parse JSON response: {e}") from e
