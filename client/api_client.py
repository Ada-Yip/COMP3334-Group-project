"""Client-side API helpers and session state for interacting with api_server.py."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from urllib import error, request


@dataclass
class ClientState:
    """Runtime state for a simple interactive client session."""

    base_url: str = "http://127.0.0.1:8000"
    current_user_id: int | None = None
    current_username: str | None = None
    next_local_message_id: int = 1
    seen_message_ids: set[int] = field(default_factory=set)


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


def register_user(base_url: str, user_name: str, password: str, public_key: str) -> dict:
    payload = {
        "user_name": user_name,
        "password": password,
        "public_key": public_key,
    }
    #  Todo: public should be generated on client sice, make a generate_localPkey() function in crypto_manager.py
    return _request_json("POST", f"{base_url}/register", payload)


def get_public_key(base_url: str, user_id: int) -> dict:
    return _request_json("GET", f"{base_url}/users/{user_id}/public_key")


#  Message body will soon get updated once basic functions are done, remember to change this part.
def send_message(
    base_url: str,
    sender_id: int,
    sender_username: str,
    receiver_id: int,
    receiver_username: str,
    ciphertext: str,
    nonce: str,
) -> dict:
    payload = {
        "sender_id": sender_id,
        "sender_username": sender_username,
        "receiver_id": receiver_id,
        "receiver_username": receiver_username,
        # Server model includes this field but does not use it while saving.
        "receiver": receiver_username,
        "ciphertext": ciphertext,
        "nonce": nonce,
    }
    return _request_json("POST", f"{base_url}/messages/send", payload)


def fetch_messages(base_url: str, user_id: int) -> dict:
    return _request_json("GET", f"{base_url}/messages/fetch/{user_id}")


def reserve_local_message_id(state: ClientState) -> int:
    """Return and advance a local message counter for CLI tracking."""
    local_id = state.next_local_message_id
    state.next_local_message_id += 1
    return local_id


#  Todo: Still not sure how to avoid collision, or do we need to consider this?
def generate_nonce() -> str:
    """Generate a random nonce string for message send calls."""
    return secrets.token_hex(12)


#  Todo: We need a login state, currently the client fetch the message by input the user-id and username.
def get_new_messages(state: ClientState, response: dict) -> list[dict]:
    """Filter fetched messages to only unseen server message IDs."""
    raw_messages = response.get("messages") if isinstance(response, dict) else None
    if not isinstance(raw_messages, list):
        return []

    new_messages: list[dict] = []
    for message in raw_messages:
        message_id = message.get("message_id")
        if not isinstance(message_id, int):
            # If an unexpected shape appears, still surface it to the CLI.
            new_messages.append(message)
            continue
        if message_id in state.seen_message_ids:
            continue
        state.seen_message_ids.add(message_id)
        new_messages.append(message)
    return new_messages
