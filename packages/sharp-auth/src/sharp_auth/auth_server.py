#!/usr/bin/env python3
"""
Sharp IoT Authentication Server - FastAPI Edition

A stateless FastAPI server that handles Sharp OAuth 2.0 authentication flow.
Supports multiple simultaneous sessions with session-based state management.
"""

import logging
import random
import string
import uuid
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Import Sharp client
import os
from sharp_core import SharpClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Sharp IoT Authentication Server",
    description="OAuth 2.0 authentication server for Sharp IoT devices",
    version="2.0.0"
)

# Templates setup
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates"))

# In-memory session storage (for demo purposes - in production use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}

# Session cleanup - remove sessions older than 1 hour
def cleanup_sessions():
    """Remove expired sessions."""
    current_time = datetime.now()
    expired_sessions = [
        session_id for session_id, session_data in sessions.items()
        if current_time - session_data.get('created_at', current_time) > timedelta(hours=1)
    ]
    for session_id in expired_sessions:
        del sessions[session_id]
        logger.info(f"Removed expired session: {session_id}")

# Pydantic models
class AuthSession(BaseModel):
    session_id: str
    step: str
    terminal_app_id: Optional[str] = None
    nonce: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

class AuthStartResponse(BaseModel):
    session_id: str
    redirect_url: str

class AuthStatusResponse(BaseModel):
    session_id: str
    step: str
    terminal_id: Optional[str] = None
    error: Optional[str] = None

class CallbackRequest(BaseModel):
    callback_url: str

class CallbackResponse(BaseModel):
    success: bool
    error: Optional[str] = None

# Sharp authentication functions
def generate_nonce(length: int = 32) -> str:
    """Generate a random nonce of specified length using alphanumeric characters."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_terminal_app_id(client: SharpClient) -> str:
    """Get the terminal app ID from the HMS API."""
    logger.info("Requesting new terminal app ID from Sharp API")
    url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/terminalAppId/"
    params = {"serviceName": "sharp-eu"}

    data = client.get_json(url, params=params)
    terminal_app_id = data.get("terminalAppId")
    logger.info(f"Received terminal app ID: {terminal_app_id}")
    return terminal_app_id

def register_terminal(client: SharpClient) -> None:
    """Register terminal data with the HMS API."""
    logger.info("Registering terminal with Sharp API")
    url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/terminal"

    # Generate random 5 character name
    random_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    logger.info(f"Generated random terminal name: {random_name}")

    data = {
        "pushId": "",
        "os": "Android",
        "osVersion": "15",
        "appName": "spremote_a_eu:1:1.0.2",
        "name": random_name,
        "permitTidLogin": 1,
        "expireSecTidLogin": 0
    }

    # Use post() instead of post_json() since this endpoint returns empty response
    response = client.post(url, json=data)
    logger.info(f"Terminal registration completed successfully (status: {response.status_code})")

def login_with_code(client: SharpClient, terminal_app_id: str, code: str, nonce: str) -> dict:
    """Perform the login with the authorization code."""
    logger.info("Performing login with authorization code")
    url = "https://eu-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta/setting/login/"
    params = {"serviceName": "sharp-eu"}
    data = {
        "terminalAppId": terminal_app_id,
        "tempAccToken": code,
        "password": nonce
    }

    result = client.post_json(url, params=params, json=data)
    logger.info("Login completed successfully")
    return result

def build_auth_url(nonce: str, session_id: str) -> str:
    """Build the authorization URL with Sharp's predefined redirect URI."""
    base_url = "https://auth-eu.global.sharp/oxauth/restv1/authorize"
    params = {
        "scope": "openid profile email",
        "client_id": "8c7f4378-5f26-4618-9854-483ad86bec0a",
        "response_type": "code",
        "redirect_uri": "sharp-cocoroair-eu://authorize",  # Sharp's predefined redirect URI
        "nonce": nonce,
        "ui_locales": "en",
        "prompt": "login"
        # Note: We can't use state parameter with Sharp's redirect URI
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_main_page(request: Request):
    """Serve the main authentication page."""
    return templates.TemplateResponse("auth.html", {"request": request})

@app.post("/start", response_model=AuthStartResponse)
async def start_auth():
    """Start a new authentication session."""
    try:
        # Cleanup old sessions
        cleanup_sessions()

        # Create new session
        session_id = str(uuid.uuid4())
        nonce = generate_nonce()

        logger.info(f"Starting new authentication session: {session_id}")

        # Initialize Sharp client
        client = SharpClient()

        # Get terminal app ID
        terminal_app_id = get_terminal_app_id(client)

        # Create session
        sessions[session_id] = {
            'step': 'auth_redirect',
            'terminal_app_id': terminal_app_id,
            'nonce': nonce,
            'error_message': None,
            'created_at': datetime.now(),
            'client': client  # Store client in session for later use
        }

        # Build auth URL
        auth_url = build_auth_url(nonce, session_id)

        # Update session state
        sessions[session_id]['step'] = 'waiting_callback'

        logger.info(f"Session {session_id} ready, redirecting to Sharp OAuth")

        return AuthStartResponse(
            session_id=session_id,
            redirect_url=auth_url
        )

    except Exception as e:
        logger.error(f"Error starting auth flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/callback/{session_id}", response_model=CallbackResponse)
async def handle_manual_callback(session_id: str, request: CallbackRequest):
    """Handle the manually pasted OAuth callback URL."""
    try:
        logger.info(f"Processing manual callback for session: {session_id}")

        if session_id not in sessions:
            logger.error(f"Invalid session ID: {session_id}")
            return CallbackResponse(success=False, error="Invalid session ID")

        session = sessions[session_id]

        # Parse the callback URL
        callback_url = request.callback_url
        if not callback_url.startswith("sharp-cocoroair-eu://authorize?"):
            return CallbackResponse(success=False, error="Invalid callback URL format")

        # Extract the code from the callback URL
        parsed_url = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        code = query_params.get('code', [None])[0]

        if not code:
            return CallbackResponse(success=False, error="No authorization code found in callback URL")

        logger.info(f"Extracted authorization code for session: {session_id}")

        # Update session state
        session['step'] = 'processing'

        # Complete the authentication flow with OAuth code
        login_result = login_with_code(
            session['client'],
            session['terminal_app_id'],
            code,
            session['nonce']
        )

        logger.info(f"Login result: {login_result}")

        # Register terminal with Sharp API
        register_terminal(session['client'])

        # Mark as successful
        session['step'] = 'success'
        logger.info(f"Authentication successful for session: {session_id}")

        return CallbackResponse(success=True)

    except Exception as e:
        logger.error(f"Error handling manual callback: {e}")
        if session_id in sessions:
            sessions[session_id]['step'] = 'error'
            sessions[session_id]['error_message'] = str(e)
        return CallbackResponse(success=False, error=str(e))

@app.get("/status/{session_id}", response_model=AuthStatusResponse)
async def get_auth_status(session_id: str):
    """Get the current status of an authentication session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    return AuthStatusResponse(
        session_id=session_id,
        step=session['step'],
        terminal_id=session.get('terminal_app_id') if session['step'] == 'success' else None,
        error=session.get('error_message')
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "active_sessions": len(sessions)}

def main():
    """Run the FastAPI authentication server."""
    logger.info("🏠 Sharp IoT Authentication Server (FastAPI)")
    logger.info("=" * 50)

    port = 8000
    logger.info(f"🌐 Starting server at http://localhost:{port}")
    logger.info("📱 The authentication page will open automatically")
    logger.info("⏹️  Press Ctrl+C to stop the server")
    logger.info("")

    # Start the server
    uvicorn.run(
        "sharp_auth.auth_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
