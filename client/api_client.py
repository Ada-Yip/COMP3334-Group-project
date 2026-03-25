"""Client-side API helpers and session state for interacting with api_server.py."""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from urllib import error, request
from datetime import datetime, timedelta
from config import SERVER_URL
from crypto_manager import CryptoManager, KeyChangeError


@dataclass
class ClientState:
    """runtime state for a simple interactive client session"""

    base_url: str = SERVER_URL
    current_user_id: int | None = None
    current_username: str | None = None
    session_token: str | None = None
    next_local_message_id: int = 1
    seen_message_ids: set[int] = field(default_factory=set)

@dataclass
class Conversation:
    """Represents a conversation with one contact."""
    sender_username: str
    last_timestamp: int
    unread_count: int
    message_list: list = field(default_factory=list)



class ClientAPI:
    """
    API wrapper that owns client session state.
    """

    def _group_messages_by_contact(self, messages: list) -> list[Conversation]:
        """Group messages by conversation partner (the other person in the conversation)."""
        conversations: dict[str, Conversation] = {}
        current_user = self.state.current_username
        for msg in messages:
            # 決定對話對象
            if msg.get("sender_username") == current_user:
                contact = msg.get("receiver_username")
            else:
                contact = msg.get("sender_username")
            if not contact:
                continue
            ts = msg.get("timestamp", 0)
            if contact not in conversations:
                conversations[contact] = Conversation(
                    sender_username=contact,
                    last_timestamp=ts,
                    unread_count=0,
                    message_list=[],
                )
            conversations[contact].message_list.append(msg)
            if ts > conversations[contact].last_timestamp:
                conversations[contact].last_timestamp = ts
        return sorted(conversations.values(), key=lambda conv: conv.last_timestamp, reverse=True)

    def __init__(self, base_url: str = SERVER_URL, state: ClientState | None = None):
        self.state: ClientState = state or ClientState(base_url=base_url)
        self.base_url: str = self.state.base_url
        self.crypto_manager = CryptoManager()

    #===============Utility Functions========================================
    def calc_time_ago(self, timestamp: int) -> str:
        """Convert unix timestamp to human-readable 'time ago' format."""
        now = int(time.time())
        diff = now - timestamp
        if diff < 60:
            return "just now"
        if diff < 3600:
            mins = diff // 60
            return f"{mins}m ago" if mins > 1 else "1m ago"
        if diff < 86400:
            hours = diff // 3600
            return f"{hours}h ago" if hours > 1 else "1h ago"
        dt = datetime.fromtimestamp(timestamp)
        today = datetime.now()
        if dt.date() == today.date():
            return f"Today {dt.strftime('%H:%M')}"
        if (today - timedelta(days=1)).date() == dt.date():
            return f"Yesterday {dt.strftime('%H:%M')}"
        return dt.strftime("%b %d")

    def _group_messages_by_sender(self, messages: list) -> list[Conversation]:
        """Group messages by sender and sort conversations by latest activity."""
        conversations: dict[str, Conversation] = {}
        for msg in messages:
            sender = msg.get("sender_username")
            if not sender:
                continue
            ts = msg.get("timestamp", 0)
            if sender not in conversations:
                conversations[sender] = Conversation(
                    sender_username=sender,
                    last_timestamp=ts,
                    unread_count=0,
                    message_list=[],
                )
            conversations[sender].message_list.append(msg)
            if ts > conversations[sender].last_timestamp:
                conversations[sender].last_timestamp = ts
        return sorted(conversations.values(), key=lambda conv: conv.last_timestamp, reverse=True)

    def get_conversations_list(self) -> list[Conversation]:
        """Fetch all messages (sent and received) for View messages only."""
        msg_response = _request_json(
            "POST",
            f"{self.base_url}/messages/conversations?offset=0&limit=10000",
            token=self.state.session_token,
        )
        if msg_response.get("status_code") != 200:
            return []
        data_payload = msg_response.get("data") or {}
        messages = data_payload.get("messages") or []
        conversations = self._group_messages_by_contact(messages)
        for conv in conversations:
            conv.unread_count = sum(
                1 for m in conv.message_list 
                if m.get("age", 0) >= 0 
                and not m.get("is_delivered", True)
                and m.get("sender_username") != self.state.current_username
            )
        return conversations

    def get_public_key_by_username(self, username: str) -> dict:
        """get public key from server by username"""
        return _request_json("GET", f"{self.base_url}/users/{username}/public_key", token=self.state.session_token)

    def get_user_name(self) -> str:
        """get user name from server"""
        return self.state.current_username

    def get_user_id(self) -> int:
        """get user id from server"""
        return self.state.current_user_id

    #===============API Functions==============================================

    def register_user(self, username: str, password: str) -> dict:
        """register user to server"""

        self.crypto_manager.initialize_for_user(username)   #generate private key and save to local storage

        payload = {
            "username": username, 
            "password": password, 
            "public_key": self.crypto_manager.get_local_public_key_b64()
            }
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
            self.crypto_manager.initialize_for_user(username)   #check if private key and counters are loaded from local storage
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

    #====================================Friend Request========================================

    def respond_friend_request(self, request_id: int, action: str) -> dict:
        """Respond to a pending friend request."""
        return _request_json(
            "POST",
            f"{self.base_url}/friend-requests/respond",
            {"request_id": request_id, "action": action},
            token=self.state.session_token
        )

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

#====================================Message========================================

    def send_message(
            self,
            receiver_username: str,
            plaintext: str,
            age: int,
    ) -> dict:
        """(R6)(R7) send message to server, responsible for handling key change detection"""
        peer_res = self.get_public_key_by_username(receiver_username)
            
        try:
            self.crypto_manager.derive_shared_key(peer_res['public_key'], receiver_username)
            return self.send_message_handling(receiver_username, plaintext, age)
        except KeyChangeError as e:
            print(f"\n[SECURITY ALERT] {e}")
            print("This means the user might have reinstalled the app, OR someone is trying to intercept your connection!")
            confirm = input("Do you still want to trust this new key and send the message? (y/n): ").strip().lower()
            if confirm == 'y':
                self.crypto_manager.derive_shared_key(peer_res['public_key'], receiver_username, force_accept = True)
                return self.send_message_handling(receiver_username, plaintext, age)
            else:
                raise ValueError("Key change detected for user: " + receiver_username)

    def send_message_handling(
        self, 
        receiver_username: str, 
        plaintext: str, 
        age: int,
    ) -> dict:
        """(R8) send message to server, responsible for incrementing message id and encrypting message"""
        current_counter = self.crypto_manager.get_and_increment_message_id()
        self.state.next_local_message_id += 1

        encrypted_text, actual_nonce = self.crypto_manager.encrypt(
            plaintext=plaintext,
            recipient_username=receiver_username,
            sender_username=self.state.current_username,
            counter=current_counter
        )
        return _request_json("POST", f"{self.base_url}/messages/send", {
            "receiver_username": receiver_username,
            "ciphertext": encrypted_text,
            "nonce": actual_nonce,
            "age": age,
            "counter": current_counter,
        }, token=self.state.session_token)

    def set_otp(self) -> dict:
        """set OTP secret for current user"""
        response = _request_json(
            "POST",
            f"{self.base_url}/OTP/set",
            {"secret": self.state.session_token},
            token=self.state.session_token
        )
        return response


    def get_otp_key(self) -> dict:
        """get OTP key for current user"""
        return _request_json(
            "POST",
            f"{self.base_url}/OTP/get-key",
            {"secret": self.state.session_token},
            token=self.state.session_token
        )

    def verify_otp(self, input_code: int) -> bool:
        """verify OTP secret for current user"""
        response = _request_json(
            "POST",
            f"{self.base_url}/OTP/verify",
            {"secret": self.state.session_token,
             "input_code": input_code},
            token=self.state.session_token
        )
        return response.get("status_code") == 200


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
