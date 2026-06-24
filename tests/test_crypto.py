import pytest
from src.crypto import A2G1_MAGIC, GCM1_MAGIC, VaultCrypto


def fast_crypto():
    return VaultCrypto(argon2_time_cost=1, argon2_memory_cost_kib=8192, argon2_parallelism=1)


def test_encryption_decryption():
    crypto = fast_crypto()
    master_password = "super_secret"
    data = b"my_secret_json_data"
    
    payload = crypto.encrypt(data, master_password)
    assert payload.startswith(A2G1_MAGIC)
    
    decrypted = crypto.decrypt(payload, master_password)
    
    assert decrypted == data
    assert payload != data

def test_legacy_gcm_fallback():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    password = "legacy_gcm_password"
    data = b"legacy_gcm_data"
    crypto = fast_crypto()

    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = crypto._derive_key(password, salt)
    encrypted_data = AESGCM(key).encrypt(nonce, data, None)
    legacy_payload = GCM1_MAGIC + salt + nonce + encrypted_data

    decrypted = crypto.decrypt(legacy_payload, password)
    assert decrypted == data

def test_legacy_fernet_fallback():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    from cryptography.fernet import Fernet
    import os
    
    password = "legacy_password"
    data = b"legacy_data"
    
    # Simulate legacy encryption
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    f = Fernet(key)
    encrypted_data = f.encrypt(data)
    
    legacy_payload = salt + encrypted_data
    
    crypto = fast_crypto()
    decrypted = crypto.decrypt(legacy_payload, password)
    assert decrypted == data

def test_wrong_password():
    crypto = fast_crypto()
    payload = crypto.encrypt(b"data", "pass1")
    import pytest
    with pytest.raises(ValueError):
        crypto.decrypt(payload, "pass2")
