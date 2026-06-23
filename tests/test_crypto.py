import pytest
from src.crypto import VaultCrypto

def test_encryption_decryption():
    crypto = VaultCrypto()
    master_password = "super_secret"
    data = b"my_secret_json_data"
    
    payload = crypto.encrypt(data, master_password)
    assert payload.startswith(b'GCM1')
    
    decrypted = crypto.decrypt(payload, master_password)
    
    assert decrypted == data
    assert payload != data

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
    
    crypto = VaultCrypto()
    decrypted = crypto.decrypt(legacy_payload, password)
    assert decrypted == data

def test_wrong_password():
    crypto = VaultCrypto()
    payload = crypto.encrypt(b"data", "pass1")
    import pytest
    with pytest.raises(ValueError):
        crypto.decrypt(payload, "pass2")
