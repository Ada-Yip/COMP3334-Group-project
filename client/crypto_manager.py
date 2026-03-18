"""
responsible for encryption
"""

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class CryptoManager:
    def __init__(self, shared_key: bytes):
        # 實際專案應透過 ECDH 生成，這裡簡化為雙方共用一個 32 bytes Key
        self.aesgcm = AESGCM(shared_key)

    def encrypt(self, plaintext: str) -> tuple[str, str]:
        """將明文加密成密文與 Nonce (Base64格式)"""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(ciphertext).decode('utf-8'), base64.b64encode(nonce).decode('utf-8')

    def decrypt(self, b64_ciphertext: str, b64_nonce: str) -> str:
        """將密文解密回明文"""
        ciphertext = base64.b64decode(b64_ciphertext)
        nonce = base64.b64decode(b64_nonce)
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')