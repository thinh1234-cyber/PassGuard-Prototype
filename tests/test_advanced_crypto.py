import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto import A2G1_MAGIC, ARGON2_HEADER, ARGON2_HASH_LEN, NONCE_SIZE, SALT_SIZE, VaultCrypto


def fast_crypto():
    return VaultCrypto(argon2_time_cost=1, argon2_memory_cost_kib=8192, argon2_parallelism=1)

def test_aes_gcm_format_and_integrity():
    crypto = fast_crypto()
    password = "super_strong_password"
    data = b"secret_data_to_be_encrypted"
    
    payload = crypto.encrypt(data, password)
    
    # 1. Check Magic Header
    assert payload.startswith(A2G1_MAGIC)
    
    # 2. Extract Components
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
    
    assert (time_cost, memory_cost_kib, parallelism) == (1, 8192, 1)
    assert len(salt) == SALT_SIZE
    assert len(nonce) == NONCE_SIZE
    # Ciphertext = raw data + 16 bytes GCM auth tag
    assert len(ciphertext) == len(data) + 16
    
    # 3. Test exact decryption
    decrypted = crypto.decrypt(payload, password)
    assert decrypted == data

def test_tamper_detection():
    crypto = fast_crypto()
    password = "password123"
    payload = crypto.encrypt(b"my_vault_data", password)
    
    # Tamper with the ciphertext (last byte)
    tampered_payload = payload[:-1] + bytes([(payload[-1] + 1) % 256])
    
    # Decryption MUST fail (GCM Auth Tag validation)
    with pytest.raises(ValueError, match="Invalid password or corrupted data"):
        crypto.decrypt(tampered_payload, password)


def test_header_tamper_detection():
    crypto = fast_crypto()
    password = "password123"
    payload = crypto.encrypt(b"my_vault_data", password)
    tampered_payload = bytearray(payload)
    tampered_payload[len(A2G1_MAGIC) + ARGON2_HEADER.size] ^= 1

    with pytest.raises(ValueError, match="Invalid password or corrupted data"):
        crypto.decrypt(bytes(tampered_payload), password)


def test_new_a2g1_payload_uses_header_aad():
    crypto = fast_crypto()
    password = "password123"
    payload = crypto.encrypt(b"my_vault_data", password)

    params_end = len(A2G1_MAGIC) + ARGON2_HEADER.size
    salt_end = params_end + SALT_SIZE
    nonce_end = salt_end + NONCE_SIZE
    salt = payload[params_end:salt_end]
    nonce = payload[salt_end:nonce_end]
    ciphertext = payload[nonce_end:]
    key = crypto._derive_argon2id_key("password123", salt, 1, 8192, 1)

    with pytest.raises(Exception):
        AESGCM(key).decrypt(nonce, ciphertext, None)

    assert AESGCM(key).decrypt(nonce, ciphertext, payload[:nonce_end]) == b"my_vault_data"


def test_early_a2g1_without_aad_still_decrypts():
    crypto = fast_crypto()
    password = "password123"
    data = b"old_a2g1_data"
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    params = ARGON2_HEADER.pack(1, 8192, 1)
    key = crypto._derive_argon2id_key(password, salt, 1, 8192, 1)
    ciphertext = AESGCM(key).encrypt(nonce, data, None)
    payload = A2G1_MAGIC + params + salt + nonce + ciphertext

    assert crypto.decrypt(payload, password) == data


def test_rejects_extreme_argon2_params_without_kdf_work():
    crypto = fast_crypto()
    payload = crypto.encrypt(b"my_vault_data", "password123")
    params = ARGON2_HEADER.pack(999, 8192, 1)
    tampered_payload = A2G1_MAGIC + params + payload[len(A2G1_MAGIC) + ARGON2_HEADER.size:]

    with pytest.raises(ValueError, match="Invalid password or corrupted data"):
        crypto.decrypt(tampered_payload, "password123")


def test_wrong_password_rejection():
    crypto = fast_crypto()
    payload = crypto.encrypt(b"important_data", "correct_pass")
    
    with pytest.raises(ValueError):
        crypto.decrypt(payload, "wrong_pass")
        
def test_argon2id_key_derivation_deterministic():
    crypto = fast_crypto()
    salt = b'\x00' * 16
    key1 = crypto._derive_argon2id_key("password", salt)
    key2 = crypto._derive_argon2id_key("password", salt)
    assert key1 == key2
    assert len(key1) == ARGON2_HASH_LEN # Must be exactly 32 bytes for AES-256
