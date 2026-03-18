"""
main entry point
"""

from client.UI import main as client_main
from server.api_server import main as server_main
from config import SERVER_HOST, SERVER_PORT
import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.api_server:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)