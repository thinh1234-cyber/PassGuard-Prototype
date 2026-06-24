import os
import base64
import struct
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


A2G1_MAGIC = b"A2G1"
GCM1_MAGIC = b"GCM1"
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 65536
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 32
ARGON2_MAX_TIME_COST = 10
ARGON2_MAX_MEMORY_COST_KIB = 262144
ARGON2_MAX_PARALLELISM = 4
SALT_SIZE = 16
NONCE_SIZE = 12
ARGON2_HEADER = struct.Struct(">III")


class VaultCrypto:
    def __init__(
        self,
        argon2_time_cost: int = ARGON2_TIME_COST,
        argon2_memory_cost_kib: int = ARGON2_MEMORY_COST_KIB,
        argon2_parallelism: int = ARGON2_PARALLELISM,
    ):
        self.argon2_time_cost = argon2_time_cost
        self.argon2_memory_cost_kib = argon2_memory_cost_kib
        self.argon2_parallelism = argon2_parallelism

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

    def _derive_argon2id_key(
        self,
        password: str,
        salt: bytes,
        time_cost: int | None = None,
        memory_cost_kib: int | None = None,
        parallelism: int | None = None,
    ) -> bytes:
        time_cost = self.argon2_time_cost if time_cost is None else time_cost
        memory_cost_kib = self.argon2_memory_cost_kib if memory_cost_kib is None else memory_cost_kib
        parallelism = self.argon2_parallelism if parallelism is None else parallelism

        if time_cost < 1 or time_cost > ARGON2_MAX_TIME_COST:
            raise ValueError("Invalid password or corrupted data")
        if parallelism < 1 or parallelism > ARGON2_MAX_PARALLELISM:
            raise ValueError("Invalid password or corrupted data")
        if memory_cost_kib < 8192 or memory_cost_kib > ARGON2_MAX_MEMORY_COST_KIB:
            raise ValueError("Invalid password or corrupted data")

        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )

    def encrypt(self, data: bytes, password: str) -> bytes:
        salt = os.urandom(SALT_SIZE)
        key = self._derive_argon2id_key(password, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(NONCE_SIZE)
        params = ARGON2_HEADER.pack(self.argon2_time_cost, self.argon2_memory_cost_kib, self.argon2_parallelism)
        header = A2G1_MAGIC + params + salt + nonce
        ciphertext = aesgcm.encrypt(nonce, data, header)
        return header + ciphertext

    def decrypt(self, payload: bytes, password: str) -> bytes:
        if payload.startswith(A2G1_MAGIC):
            min_len = len(A2G1_MAGIC) + ARGON2_HEADER.size + SALT_SIZE + NONCE_SIZE + 16
            if len(payload) < min_len:
                raise ValueError("Invalid password or corrupted data")

            params_start = len(A2G1_MAGIC)
            params_end = params_start + ARGON2_HEADER.size
            salt_start = params_end
            salt_end = salt_start + SALT_SIZE
            nonce_start = salt_end
            nonce_end = nonce_start + NONCE_SIZE

            time_cost, memory_cost_kib, parallelism = ARGON2_HEADER.unpack(payload[params_start:params_end])
            salt = payload[salt_start:salt_end]
            nonce = payload[nonce_start:nonce_end]
            ciphertext = payload[nonce_end:]

            try:
                key = self._derive_argon2id_key(password, salt, time_cost, memory_cost_kib, parallelism)
                aesgcm = AESGCM(key)
                header = payload[:nonce_end]
                try:
                    return aesgcm.decrypt(nonce, ciphertext, header)
                except Exception:
                    # Compatibility path for early A2G1 vaults saved before header AAD was added.
                    return aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                raise ValueError("Invalid password or corrupted data") from e

        if payload.startswith(GCM1_MAGIC):
            if len(payload) < len(GCM1_MAGIC) + SALT_SIZE + NONCE_SIZE + 16:
                raise ValueError("Invalid password or corrupted data")

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
