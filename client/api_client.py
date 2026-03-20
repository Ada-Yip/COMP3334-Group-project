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
    session_token: str | None = None
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
        return _request_json("GET", f"{self.base_url}/users/{user_id}/public_key", token = self.state.session_token)

    def get_user_name(self) -> str:
        """get user name from server"""
        return self.state.current_username

    def get_user_id(self) -> int:
        """get user id from server"""
        return self.state.current_user_id

    def generate_nonce(self) -> str:
        #TODO: do actual nonce generation
        """generate nonce"""
        return secrets.token_hex(12)

    #===============API Functions==============================================

    def register_user(self, username: str, password: str) -> dict:
        """register user to server"""
        payload = {"username": username, "password": password, "public_key": self.generate_local_public_key()}
        response = _request_json("POST", f"{self.base_url}/register", payload)
        if response.get("status_code") == 200:
            data = response.get("data")
            self.state.current_user_id = data["user_id"]
            self.state.current_username = data["username"]
        return response

    def login(self, username: str, password: str) -> dict:  # TODO: Encrypted login method is not yet done here.
        payload = {"username": username, "password": password}
        response = _request_json("POST", f"{self.base_url}/login", payload)
        if response.get("status_code") == 200:
            data = response.get("data")
            self.state.current_user_id = data["user_id"]
            self.state.current_username = data["username"]
            self.state.session_token = data["token"]
        return response

    def logout(self) -> dict:
        """logout user from server"""
        response = _request_json("POST", f"{self.base_url}/logout", token=self.state.session_token)
        if response.get("status_code") == 200:
            self.state.session_token = None
            self.state.current_user_id = None
            self.state.current_username = None
            print("You have been logged out successfully")
        return response

    def send_message(
            self,
            receiver_username: str,
            ciphertext: str,
    ) -> dict:
        """send message to server"""
        #TODO: nonce need fixed later
        return _request_json("POST", f"{self.base_url}/messages/send", {
            "receiver_username": receiver_username,
            "ciphertext": ciphertext,
            "nonce": self.generate_nonce(),
        }, token = self.state.session_token)

    def fetch_messages_all(self) -> dict:
        """fetch all messages from server"""
        msg_response = _request_json("POST", f"{self.base_url}/messages/fetch?unseen_only=false", token = self.state.session_token)
        if msg_response.get("status_code") == 200:
            messages = msg_response.get("data").get("messages")
            self.show_messages(messages)
        return msg_response

    def fetch_messages_unseen(self) -> dict:
        """fetch only unseen messages from server"""
        msg_response = _request_json("POST", f"{self.base_url}/messages/fetch?unseen_only=true", token = self.state.session_token)
        if msg_response.get("status_code") == 200:
            messages = msg_response.get("data").get("messages")
            self.show_messages(messages)
        return msg_response

    #TODO: add decryption for messages
    def show_messages(self, messages: dict) -> None:
        """show messages"""
        if not messages:
            print("No messages to show")
            return
        print("===========Messages===========\n")
        print(f"Total messages: {len(messages)}")
        for message in messages:
            print(f"From: {message.get('sender_username')}")
            print(f"To: {message.get('receiver_username')}")
            print(f"Message: {message.get('plaintext')}")
            print("--------------------------------")
        print("===========End of Messages===========\n")


def _request_json(
    method: str, 
    url: str, 
    payload: dict | None = None, 
    token: str | None = None
) -> dict:
    """
    Send an HTTP request and parse JSON response to dictionary
    It will add authorization header if token is provided
    """
    data = None
    headers = {"Accept": "application/json"}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=data, headers=headers, method=method)

    try:
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            if isinstance(parsed, dict):
                return {"status_code": response.status, **parsed}  #return unpacked dictionary
            return {"status_code": response.status, "data": parsed}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {}

        if isinstance(parsed, dict) and "detail" in parsed:
            detail = parsed.get("detail")
        else:
            detail = parsed or (body or str(exc))

        return {"status_code": exc.code, "detail": detail}
    except error.URLError as exc:
        return {"status_code": 0, "detail": {"error": str(exc)}}


#TODO: fix it later, currently not used
def reserve_local_message_id(state: ClientState) -> int:
    """Return and advance a local message counter for CLI tracking."""
    local_id = state.next_local_message_id
    state.next_local_message_id += 1
    return local_id
