# Sharp Auth

FastAPI-based authentication server for Sharp IoT device OAuth 2.0 flow.

## Overview

`sharp-auth` provides a web-based authentication server that handles the OAuth 2.0 flow with Sharp's EU authentication service. Due to Sharp's mobile app redirect scheme (`sharp-cocoroair-eu://authorize`), the authentication requires manual callback URL copying.

## Features

- **FastAPI Server**: Modern async web framework with automatic API documentation
- **Session Management**: Multi-user support with in-memory session storage
- **Stateless Design**: Each authentication session is independent
- **Web UI**: User-friendly HTML interface with real-time status updates
- **Terminal Registration**: Automatic terminal creation with random 5-character names

## Installation

Install as part of the Sharp IoT workspace:

```bash
uv sync
```

## Usage

### Start the Server

```bash
uv run sharp-auth
```

The server:
- Starts at `http://localhost:8000`
- Opens the authentication page automatically in your browser
- Provides RESTful API endpoints for integration

### Authentication Flow

1. **Start Authentication**:
   - Click "Start Authentication" button on the web UI
   - Server requests new terminal app ID from Sharp API
   - Generates OAuth nonce for security
   - Redirects to Sharp's OAuth login page

2. **Login with Sharp Account**:
   - Enter your Sharp IoT credentials
   - Authorize the application
   - Browser redirects to `sharp-cocoroair-eu://authorize?code=...`

3. **Complete Authentication**:
   - Copy the entire callback URL from browser
   - Paste into the authentication page
   - Server exchanges code for access token
   - Server registers terminal with random name
   - Terminal ID displayed on success page

### Terminal ID

The terminal ID returned by this server is used by:
- `sharp-cli`: Command-line device control
- `sharp-homeassistant`: Home Assistant integration
- Direct API access via `sharp-devices`

Terminal IDs don't expire but can be invalidated if the terminal is deleted from Sharp's cloud.

## API Endpoints

### Web Interface

- `GET /`: Main authentication page (HTML)

### REST API

#### Start Authentication Session
```http
POST /start
Response: {
    "session_id": "uuid-v4",
    "redirect_url": "https://auth-eu.global.sharp/..."
}
```

#### Submit Callback URL
```http
POST /callback/{session_id}
Body: {
    "callback_url": "sharp-cocoroair-eu://authorize?code=..."
}
Response: {
    "success": true,
    "error": null
}
```

#### Check Session Status
```http
GET /status/{session_id}
Response: {
    "session_id": "uuid",
    "step": "success",
    "terminal_id": "terminal-id-here",
    "error": null
}
```

#### Health Check
```http
GET /health
Response: {
    "status": "healthy",
    "active_sessions": 3
}
```

## Session States

Authentication sessions progress through these states:

1. **auth_redirect**: Initial redirect to Sharp OAuth
2. **waiting_callback**: Waiting for user to paste callback URL
3. **processing**: Exchanging code for token and registering terminal
4. **success**: Authentication complete, terminal ID available
5. **error**: Authentication failed (see error_message)

## Session Management

- **Storage**: In-memory dictionary (not persistent across restarts)
- **Cleanup**: Sessions older than 1 hour are automatically removed
- **Concurrent Sessions**: Multiple users can authenticate simultaneously

## Configuration

### Server Settings

Default configuration (modify in `auth_server.py:285-301`):

```python
host = "0.0.0.0"
port = 8000
```

### OAuth Parameters

Sharp OAuth configuration (automatically set):

```python
client_id = "8c7f4378-5f26-4618-9854-483ad86bec0a"
redirect_uri = "sharp-cocoroair-eu://authorize"
scope = "openid profile email"
```

## Templates

Web UI templates are located in `templates/` directory:
- `auth.html`: Main authentication page with JavaScript for session handling

## Architecture

### Authentication Process

```
User → FastAPI Server → Sharp OAuth → User (login) → Browser Callback →
User (copy URL) → FastAPI Server → Sharp API (token exchange) →
Sharp API (terminal registration) → Terminal ID → User
```

### API Calls Made

1. **Get Terminal App ID**:
   ```
   GET https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/terminalAppId/
   ```

2. **Login with Code**:
   ```
   POST https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/login/
   Body: {terminalAppId, tempAccToken, password: nonce}
   ```

3. **Register Terminal**:
   ```
   POST https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/terminal
   Body: {pushId, os, osVersion, appName, name, permitTidLogin, expireSecTidLogin}
   ```

## Dependencies

- `sharp-core`: HTTP client and constants
- `fastapi>=0.104.0`: Web framework
- `uvicorn>=0.24.0`: ASGI server
- `jinja2>=3.1.0`: Template engine

## Development

### Run in Development Mode

```bash
uv run python packages/sharp-auth/src/sharp_auth/auth_server.py
```

### API Documentation

FastAPI provides automatic API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing

```bash
# Test imports
uv run python -c "from sharp_auth.auth_server import app; print('Import successful')"

# Start server
uv run sharp-auth
```

## Troubleshooting

### Port Already in Use

Change the port in `auth_server.py`:
```python
port = 8001  # Or any available port
```

### Template Not Found

Ensure templates directory exists:
```bash
ls packages/sharp-auth/templates/auth.html
```

### Session Expired

Sessions expire after 1 hour. Start a new authentication flow.

### OAuth Error

- Verify internet connectivity
- Check Sharp service status
- Ensure credentials are correct
- Try clearing browser cookies for Sharp domain

## Security Notes

- Sessions stored in memory (not persistent)
- Nonce generated per session for CSRF protection
- HTTPS not required for localhost (Sharp OAuth allows it)
- Terminal IDs should be treated as sensitive credentials

## Production Considerations

For production deployment:
- Use Redis or database for session storage
- Implement persistent session cleanup
- Add HTTPS with valid certificate
- Add rate limiting
- Add authentication for the server itself
- Store terminal IDs securely

## License

Part of the Sharp IoT device control workspace. Sharp IoT is a trademark of Sharp Corporation.
