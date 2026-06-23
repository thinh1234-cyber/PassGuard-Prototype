import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class VaultCrypto:
    def _derive_key(self, password: str, salt: bytes, as_base64: bool = False) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = kdf.derive(password.encode())
        if as_base64:
            return base64.urlsafe_b64encode(key)
        return key

    def encrypt(self, data: bytes, password: str) -> bytes:
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return b'GCM1' + salt + nonce + ciphertext

    def decrypt(self, payload: bytes, password: str) -> bytes:
        if payload.startswith(b'GCM1'):
            salt = payload[4:20]
            nonce = payload[20:32]
            ciphertext = payload[32:]
            key = self._derive_key(password, salt)
            aesgcm = AESGCM(key)
            try:
                return aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                raise ValueError("Invalid password or corrupted data") from e
        else:
            # Legacy Fernet fallback
            salt = payload[:16]
            encrypted_data = payload[16:]
            key = self._derive_key(password, salt, as_base64=True)
            f = Fernet(key)
            try:
                return f.decrypt(encrypted_data)
            except Exception as e:
                raise ValueError("Invalid password or corrupted data") from e
