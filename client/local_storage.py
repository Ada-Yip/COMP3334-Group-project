"""
for private key + log history
"""
import json
import os
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519

LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "local_data_storage")


def _get_local_data_path(username: str) -> str:
    return os.path.join(LOCAL_STORAGE_DIR, f"{username}_local_data.json")


def save_client_data(username: str, private_key: x25519.X25519PrivateKey, counters: dict, next_message_id: int):
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
        "next_message_id": next_message_id
    }
    with open(filename, 'w') as f:
        json.dump(data, f)

def load_client_data(username: str) -> tuple:
    """load private key and counters from local file"""
    filename = _get_local_data_path(username)
    if not os.path.exists(filename):
        return None, None, 1
    
    with open(filename, 'r') as f:
        data = json.load(f)
        
    priv_bytes = base64.b64decode(data["private_key_b64"])
    private_key = x25519.X25519PrivateKey.from_private_bytes(priv_bytes)
    counters = data.get("counters", {})
    next_message_id = data.get("next_message_id", 1)
    return private_key, counters, next_message_id