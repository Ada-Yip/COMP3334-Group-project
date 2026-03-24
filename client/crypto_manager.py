"""
responsible for encryption
"""

import base64
import os
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from local_storage import load_client_data, save_client_data

class CryptoManager:
    def __init__(self):
        self.private_key = None
        self.public_key = None 
        self.session_keys = {}  #store keys for each peer
        self.peer_counters = {} #store counters for each peer
        self.current_username = None
        self.next_local_message_id = 1

    def initialize_for_user(self, username: str):
        #avoid re-initialization
        if self.current_username == username and self.private_key is not None:
            return
            
        self.current_username = username
        priv_key, counters, next_message_id = load_client_data(username)

        if priv_key:
            self.private_key = priv_key
            self.peer_counters = counters
            self.next_local_message_id = next_message_id
        else:
            self.private_key = x25519.X25519PrivateKey.generate()
            self.peer_counters = {}
            save_client_data(self.current_username, self.private_key, self.peer_counters, self.next_local_message_id)
        
        self.public_key = self.private_key.public_key()
        
    def get_local_public_key_b64(self) -> str:
        key_bytes = self.public_key.public_bytes_raw()
        return base64.b64encode(key_bytes).decode('utf-8')

    def get_and_increment_message_id(self) -> int:
        """get current counter and increment it"""
        current = self.next_local_message_id
        self.next_local_message_id += 1
        save_client_data(self.current_username, self.private_key, self.peer_counters, self.next_local_message_id)
        return current

    
    def derive_shared_key(self, peer_public_key_b64: str, peer_username: str) -> bytes:
        """ECDH to derive shared key"""
        peek_pk_bytes = base64.b64decode(peer_public_key_b64)
        peer_pk = x25519.X25519PublicKey.from_public_bytes(peek_pk_bytes)
        shared_key = self.private_key.exchange(peer_pk)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"session_key_v1",
        ).derive(shared_key)

        self.session_keys[peer_username] = derived_key
        return derived_key
    
    def encrypt(
        self, plaintext: str, 
        recipient_username: str, 
        sender_username: str, 
        counter: int
        ) -> tuple[str, str]:
        """(R8) use authenticated encryption (AEAD) and bind metadata"""
        key = self.session_keys.get(recipient_username)
        if not key:
            raise ValueError("No session key for this recipient")

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        
        # (R8) build Associated Data (AD)
        ad_dict = {
            "s": sender_username,
            "r": recipient_username,
            "c": counter
        }
        ad_bytes = json.dumps(ad_dict, sort_keys=True).encode('utf-8')
        
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), ad_bytes)
        
        return base64.b64encode(ciphertext).decode('utf-8'), base64.b64encode(nonce).decode('utf-8')
    
    def decrypt(
        self, 
        b64_ciphertext: str, 
        b64_nonce: str, 
        sender_username: str, 
        recipient_username: str, 
        counter: int
        ) -> str:
        """(R8/R9) decrypt and verify integrity"""
        key = self.session_keys.get(sender_username)
        if not key:
            raise ValueError("No session key for this sender")

        last_seen_counter = self.peer_counters.get(sender_username, 0)
        if counter <= last_seen_counter:
            raise ValueError(f"Replay attack detected, counter {counter} <= last seen counter {last_seen_counter}")

        try:
            aesgcm = AESGCM(key)
            ciphertext = base64.b64decode(b64_ciphertext)
            nonce = base64.b64decode(b64_nonce)
            ad_dict = {"s": sender_username, "r": recipient_username, "c": counter}
            ad_bytes = json.dumps(ad_dict, sort_keys=True).encode('utf-8')
            plaintext = aesgcm.decrypt(nonce, ciphertext, ad_bytes) #verify integrity

            self.peer_counters[sender_username] = counter
            save_client_data(self.current_username, self.private_key, self.peer_counters, self.next_local_message_id)
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError("Decryption failed: " + str(e))