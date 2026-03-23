"""Client-side API helpers and session state for interacting with api_server.py."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from urllib import error, request
from datetime import datetime
from config import SERVER_URL, SHARED_SECRET
from crypto_manager import CryptoManager


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
        self.crypto_manager = CryptoManager(shared_key=SHARED_SECRET)

    #===============Utility Functions========================================
    def generate_local_public_key(self) -> str:
        """generate local public key"""
        #TODO: do actual key generation
        return "dummy_key"

    def get_public_key(self, user_id: int) -> dict:
        """get public key from server"""
        return _request_json("GET", f"{self.base_url}/users/{user_id}/public_key", token=self.state.session_token)

    def get_user_name(self) -> str:
        """get user name from server"""
        return self.state.current_username

    def get_user_id(self) -> int:
        """get user id from server"""
        return self.state.current_user_id

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

    def login(self, username: str, password: str) -> dict:  
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

    ### edited friend request logic ###
    def respond_friend_request(self, request_id: int, action: str) -> dict:
        """Respond to a pending friend request."""
        return _request_json(
            "POST",
            f"{self.base_url}/friend-requests/respond",
            {"request_id": request_id, "action": action},
            token=self.state.session_token
        )

    ### JJ friend ###
    def send_friend_request(self, to_username: str) -> dict:
        """Send a friend request to another user."""
        return _request_json(
            "POST",
            f"{self.base_url}/friend-requests/send",
            {"to_username": to_username},
            token=self.state.session_token
        )
    
    def get_received_requests(self) -> dict:
        """Get all pending friend requests received by current user."""
        return _request_json(
            "GET",
            f"{self.base_url}/friend-requests/received",
            token=self.state.session_token
        )

    def get_sent_requests(self) -> dict:
        """Get all pending friend requests sent by current user."""
        return _request_json(
            "GET",
            f"{self.base_url}/friend-requests/sent",
            token=self.state.session_token
        )

    def get_friends(self) -> dict:
        """Get list of accepted friends."""
        return _request_json(
            "GET",
            f"{self.base_url}/friends",
            token=self.state.session_token
        )

    def remove_friend(self, friend_username: str) -> dict:
        """Remove an existing friend."""
        return _request_json(
            "POST",
            f"{self.base_url}/friends/remove",
            {"friend_username": friend_username},
            token=self.state.session_token
        )

    def block_user(self, block_username: str) -> dict:
        """Block another user."""
        return _request_json(
            "POST",
            f"{self.base_url}/users/block",
            {"block_username": block_username},
            token=self.state.session_token
        )

    def unblock_user(self, block_username: str) -> dict:
        """Unblock a previously blocked user."""
        return _request_json(
            "POST",
            f"{self.base_url}/users/unblock",
            {"block_username": block_username},
            token=self.state.session_token
        )
    ### JJ friend end ###

    def send_message(
            self,
            receiver_username: str,
            plaintext: str,
            age: int,
    ) -> dict:
        """send message to server"""
        encrypted_text, actual_nonce = self.crypto_manager.encrypt(plaintext)
        return _request_json("POST", f"{self.base_url}/messages/send", {
            "receiver_username": receiver_username,
            "ciphertext": encrypted_text,
            "nonce": actual_nonce,
            "age": age,
        }, token=self.state.session_token)

    def fetch_messages_all(self) -> dict:
        """fetch all messages from server"""
        msg_response = _request_json("POST", f"{self.base_url}/messages/fetch?unseen_only=false",
                                     token=self.state.session_token)
        if msg_response.get("status_code") == 200:
            data_payload = msg_response.get("data") or {}
            self.show_messages(data_payload)
        return msg_response

    def fetch_messages_unseen(self) -> dict:
        """fetch only unseen messages from server"""
        msg_response = _request_json("POST", f"{self.base_url}/messages/fetch?unseen_only=true",
                                     token=self.state.session_token)
        if msg_response.get("status_code") == 200:
            data_payload = msg_response.get("data") or {}
            self.show_messages(data_payload)
        return msg_response

    def show_messages(self, data_payload: dict) -> None:
        """
        show messages, decrypt ciphertext and nonce
        """
        if not data_payload:
            print("No messages to show")
            return
        print("===========Messages===========\n")
        messages = data_payload.get("messages") or []
        unseen_count = data_payload.get("unseen_count")
        print(f"Total messages: {len(messages)}")
        if unseen_count is None:
            print("Total unseesn: N/A")
        else:
            print(f"Total unseesn: {unseen_count}")
        for message in messages:
            sender = message.get('sender_username')
            receiver = message.get('receiver_username')
            ciphertext = message.get('ciphertext')
            nonce = message.get('nonce')
            timestamp = message.get('timestamp')
            age = message.get('age')

            print(f"From: {sender}")
            print(f"To: {receiver}")
            try:
                sent_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                if age < 0:
                    print(f"Message: [Expired Message]")
                    print(f"Sent at {sent_time}, expired {abs(age)} seconds ago")
                elif ciphertext and nonce:
                    plaintext = self.crypto_manager.decrypt(ciphertext, nonce)
                    print(f"Message: {plaintext}")
                    print(f"Sent at {sent_time}")
                    print(f"Expires in {age} seconds" if age > 0 else "")
                else:
                    print(f"Message: [Error] Missing ciphertext or nonce")
            except Exception as e:
                print(f"Message: [Decryption Failed - Data corrupted or wrong key]")
                print(f"Ciphertext: {ciphertext}")  #TODO: for debug, delete later
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
