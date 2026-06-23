import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

class VaultCrypto:
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data: bytes, password: str) -> tuple[bytes, bytes]:
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted_data = f.encrypt(data)
        return salt, encrypted_data

    def decrypt(self, encrypted_data: bytes, password: str, salt: bytes) -> bytes:
        key = self._derive_key(password, salt)
        f = Fernet(key)
        try:
            return f.decrypt(encrypted_data)
        except Exception as e:
            raise ValueError("Invalid password or corrupted data") from e
