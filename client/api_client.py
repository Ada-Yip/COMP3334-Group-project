"""Client-side API helpers and session state for interacting with api_server.py."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from urllib import error, request
from config import SERVER_URL


@dataclass
class ClientState:
    """runtime state for a simple interactive client session"""

    base_url: str = SERVER_URL
    current_user_id: int | None = None
    current_username: str | None = None
    next_local_message_id: int = 1
    seen_message_ids: set[int] = field(default_factory=set)


class ClientAPI:
    """
    API wrapper that owns client session state.
    """

    def __init__(self, base_url: str = SERVER_URL, state: ClientState | None = None):
        self.state: ClientState = state or ClientState(base_url=base_url)
        self.base_url: str = self.state.base_url

#===============Utility Functions========================================
    def generate_local_public_key(self) -> str:
        """generate local public key"""
        #TODO: do actual key generation
        return "dummy_key"

    def get_public_key(self, user_id: int) -> dict:
        """get public key from server"""
        return _request_json("GET", f"{self.base_url}/users/{user_id}/public_key")


    def generate_nonce(self) -> str:
        #TODO: do actual nonce generation
        """generate nonce"""
        return secrets.token_hex(12)



#===============API Functions==============================================

    def register_user(self, username: str, password: str) -> dict:
        """register user to server"""
        payload = {"username": username, "password": password, "public_key": self.generate_local_public_key()}
        return _request_json("POST", f"{self.base_url}/register", payload)

    def send_message(
        self,        
        receiver_username: str,
        ciphertext: str,
    ) -> dict:
        """send message to server"""
        #TODO: nonce need fixed later
        return _request_json("POST", f"{self.base_url}/messages/send", {
            "sender_id": self.state.current_user_id,
            "sender_username": self.state.current_username,
            "receiver_username": receiver_username,
            "ciphertext": ciphertext,
            "nonce": self.generate_nonce(),
        })

    def fetch_messages_all(self) -> dict:
        """fetch all messages from server"""
        payload = {
            "user_id": self.state.current_user_id,
            "unseen_only": False,
        }
        return self._request_json("GET", f"{self.base_url}/messages/fetch", payload)

    def fetch_messages_unseen(self) -> dict:
        """fetch only unseen messages from server"""
        payload = {
            "user_id": self.state.current_user_id,
            "unseen_only": True,
        }
        return self._request_json("GET", f"{self.base_url}/messages/fetch", payload)

def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    """Send an HTTP request and parse JSON response."""
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=data, headers=headers, method=method)

    #  Encoding stuff, should not be a problem
    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = {"error": body or str(exc)}
        return {"status_code": exc.code, "detail": detail}
    except error.URLError as exc:
        return {"status_code": 0, "detail": {"error": str(exc)}}

def reserve_local_message_id(state: ClientState) -> int:
    """Return and advance a local message counter for CLI tracking."""
    local_id = state.next_local_message_id
    state.next_local_message_id += 1
    return local_id