"""
for private key + log history
"""
import json
import os
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from typing import Optional

LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "local_data_storage")


def _get_local_data_path(username: str) -> str:
    return os.path.join(LOCAL_STORAGE_DIR, f"{username}_local_data.json")


def save_client_data(
    username: str, 
    private_key: x25519.X25519PrivateKey, 
    counters: Optional[dict] = {}, 
    next_message_id: Optional[int] = 1, 
    known_keys: Optional[dict] = {}):
    """store private key and counters to local file"""
    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    filename = _get_local_data_path(username)
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    data = {
        "private_key_b64": base64.b64encode(priv_bytes).decode('utf-8'),
        "counters": counters,
        "next_message_id": next_message_id,
        "known_keys": known_keys
    }
    with open(filename, 'w') as f:
        json.dump(data, f)

def load_client_data(username: str) -> tuple:
    """load private key and counters from local file"""
    filename = _get_local_data_path(username)
    if not os.path.exists(filename):
        return None, None, 1, {}
    
    with open(filename, 'r') as f:
        data = json.load(f)
        
    priv_bytes = base64.b64decode(data["private_key_b64"])
    private_key = x25519.X25519PrivateKey.from_private_bytes(priv_bytes)
    counters = data.get("counters", {})
    next_message_id = data.get("next_message_id", 1)
    known_keys = data.get("known_keys", {})
    return private_key, counters, next_message_id, known_keys

### Verified contacts management ###
def get_verified_contacts_file(username: str) -> str:
    """Get the file path for verified contacts."""
    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    return os.path.join(LOCAL_STORAGE_DIR, f"{username}_verified_contacts.json")


def save_verified_contacts(username: str, verified_contacts: set):
    """Save the set of verified contact usernames to local file."""
    filename = get_verified_contacts_file(username)
    data = {"verified_contacts": list(verified_contacts)}
    with open(filename, 'w') as f:
        json.dump(data, f)


def load_verified_contacts(username: str) -> set:
    """Load the set of verified contact usernames from local file."""
    filename = get_verified_contacts_file(username)
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r') as f:
        data = json.load(f)
    return set(data.get("verified_contacts", []))


def add_verified_contact(username: str, contact_username: str):
    """Add a contact to the verified list."""
    verified = load_verified_contacts(username)
    verified.add(contact_username)
    save_verified_contacts(username, verified)


def remove_verified_contact(username: str, contact_username: str):
    """Remove a contact from the verified list."""
    verified = load_verified_contacts(username)
    verified.discard(contact_username)
    save_verified_contacts(username, verified)


def is_contact_verified(username: str, contact_username: str) -> bool:
    """Check if a contact is verified."""
    verified = load_verified_contacts(username)
    return contact_username in verified