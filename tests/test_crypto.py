import pytest
from src.crypto import VaultCrypto

def test_encryption_decryption():
    crypto = VaultCrypto()
    master_password = "super_secret"
    data = b"my_secret_json_data"
    
    salt, encrypted = crypto.encrypt(data, master_password)
    decrypted = crypto.decrypt(encrypted, master_password, salt)
    
    assert decrypted == data
    assert encrypted != data

def test_wrong_password():
    crypto = VaultCrypto()
    salt, encrypted = crypto.encrypt(b"data", "pass1")
    with pytest.raises(ValueError):
        crypto.decrypt(encrypted, "pass2", salt)
