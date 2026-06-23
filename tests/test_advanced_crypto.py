import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto import VaultCrypto

def test_aes_gcm_format_and_integrity():
    crypto = VaultCrypto()
    password = "super_strong_password"
    data = b"secret_data_to_be_encrypted"
    
    payload = crypto.encrypt(data, password)
    
    # 1. Check Magic Header
    assert payload.startswith(b'GCM1')
    
    # 2. Extract Components
    salt = payload[4:20]
    nonce = payload[20:32]
    ciphertext = payload[32:]
    
    assert len(salt) == 16
    assert len(nonce) == 12
    # Ciphertext = raw data + 16 bytes GCM auth tag
    assert len(ciphertext) == len(data) + 16
    
    # 3. Test exact decryption
    decrypted = crypto.decrypt(payload, password)
    assert decrypted == data

def test_tamper_detection():
    crypto = VaultCrypto()
    password = "password123"
    payload = crypto.encrypt(b"my_vault_data", password)
    
    # Tamper with the ciphertext (last byte)
    tampered_payload = payload[:-1] + bytes([(payload[-1] + 1) % 256])
    
    # Decryption MUST fail (GCM Auth Tag validation)
    with pytest.raises(ValueError, match="Invalid password or corrupted data"):
        crypto.decrypt(tampered_payload, password)

def test_wrong_password_rejection():
    crypto = VaultCrypto()
    payload = crypto.encrypt(b"important_data", "correct_pass")
    
    with pytest.raises(ValueError):
        crypto.decrypt(payload, "wrong_pass")
        
def test_key_derivation_deterministic():
    crypto = VaultCrypto()
    salt = b'\x00' * 16
    key1 = crypto._derive_key("password", salt)
    key2 = crypto._derive_key("password", salt)
    assert key1 == key2
    assert len(key1) == 32 # Must be exactly 32 bytes for AES-256
