"""
config for testing the project
"""
#command: uvicorn server.api_server:app --reload
SERVER_HOST = "http://127.0.0.1"
SERVER_PORT = 8000
SERVER_URL = f"{SERVER_HOST}:{SERVER_PORT}"
SHARED_SECRET = b"12345678901234567890123456789012" 