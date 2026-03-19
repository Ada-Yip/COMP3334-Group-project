"""
config for testing the project
"""
#command: uvicorn server.api_server:app --reload

# Uvicorn's `host` expects a hostname/IP only (no scheme like "http://").
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000

# Client-facing base URL (includes scheme).
SERVER_BASE_URL = f"http://{SERVER_HOST}"
SERVER_URL = f"{SERVER_BASE_URL}:{SERVER_PORT}"
SHARED_SECRET = b"12345678901234567890123456789012" 

# Session TTL (seconds) for sliding refresh
TOKEN_TTL_SECONDS = 300  # default 5 minutes