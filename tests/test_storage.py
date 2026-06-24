import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.storage import VaultStorage
from src.models import Vault, Entry, Account
from src.crypto import A2G1_MAGIC, GCM1_MAGIC, VaultCrypto


def fast_crypto():
    return VaultCrypto(argon2_time_cost=1, argon2_memory_cost_kib=8192, argon2_parallelism=1)


def make_storage(path):
    storage = VaultStorage(str(path))
    storage.crypto = fast_crypto()
    return storage


def legacy_gcm_payload(vault, password):
    crypto = fast_crypto()
    data = vault.model_dump_json().encode("utf-8")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = crypto._derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, data, None)
    return GCM1_MAGIC + salt + nonce + ciphertext

def test_save_and_load_vault(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="T", accounts=[Account(username="U", password="P")])])
    
    storage.save(vault, "master")
    assert os.path.exists(vault_path)
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    
    loaded_vault = storage.load("master")
    assert loaded_vault.entries[0].title == "T"


def test_load_recovers_from_backup_when_main_vault_is_missing(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="BackupOnly")])

    storage.save(vault, "master")
    backup_path = tmp_path / "vault.luupass.bak1"
    backup_path.write_bytes(vault_path.read_bytes())
    vault_path.unlink()

    loaded_vault = storage.load("master")

    assert loaded_vault.entries[0].title == "BackupOnly"
    assert vault_path.exists()
    assert vault_path.read_bytes() == backup_path.read_bytes()


def test_import_valid_vault_replaces_current_vault(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    import_path = tmp_path / "import.luupass"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(
        Vault(entries=[Entry(title="Imported", accounts=[Account(username="u", password="p")])]),
        "import-pass",
    )

    imported_vault = storage.import_vault(str(import_path), "import-pass")

    assert imported_vault.entries[0].title == "Imported"
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    assert storage.load("import-pass").entries[0].title == "Imported"
    with pytest.raises(ValueError):
        storage.load("current-pass")


def test_import_vault_payload_replaces_current_vault(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    import_path = tmp_path / "import.luupass"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="ImportedPayload")]), "import-pass")

    imported_vault = storage.import_vault_payload(import_path.read_bytes(), "import-pass")

    assert imported_vault.entries[0].title == "ImportedPayload"
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    assert storage.load("import-pass").entries[0].title == "ImportedPayload"


def test_import_wrong_password_does_not_overwrite_current_vault(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    import_path = tmp_path / "import.luupass"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="Imported")]), "import-pass")
    original_payload = vault_path.read_bytes()

    with pytest.raises(ValueError, match="File import không hợp lệ"):
        storage.import_vault(str(import_path), "wrong-pass")

    assert vault_path.read_bytes() == original_payload
    assert storage.load("current-pass").entries[0].title == "Current"


def test_import_legacy_gcm_vault_reencrypts_to_argon2id(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    import_path = tmp_path / "legacy_import.luupass"
    storage = make_storage(vault_path)
    legacy_vault = Vault(entries=[Entry(title="Legacy")])

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_path.write_bytes(legacy_gcm_payload(legacy_vault, "legacy-pass"))

    imported_vault = storage.import_vault(str(import_path), "legacy-pass")

    assert imported_vault.entries[0].title == "Legacy"
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    assert storage.load("legacy-pass").entries[0].title == "Legacy"
