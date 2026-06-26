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
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="T", accounts=[Account(username="U", password="P")])])

    storage.save(vault, "master")
    assert os.path.exists(vault_path)
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)

    loaded_vault = storage.load("master")
    assert loaded_vault.entries[0].title == "T"


def test_load_recovers_from_backup_when_main_vault_is_missing(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="BackupOnly")])

    storage.save(vault, "master")
    backup_path = tmp_path / "vault.passguard.bak1"
    backup_path.write_bytes(vault_path.read_bytes())
    vault_path.unlink()

    loaded_vault = storage.load("master")

    assert loaded_vault.entries[0].title == "BackupOnly"
    assert vault_path.exists()
    assert vault_path.read_bytes() == backup_path.read_bytes()


def test_verify_backups_reports_valid_and_corrupt_backups(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="Backup")])

    storage.save(vault, "master")
    backup_path = tmp_path / "vault.passguard.bak1"
    backup_path.write_bytes(vault_path.read_bytes())
    corrupt_path = tmp_path / "vault.passguard.bak2"
    corrupt_path.write_bytes(b"not a vault")

    results = storage.verify_backups("master")

    assert results[0]["exists"] is True
    assert results[0]["valid"] is True
    assert results[0]["entries"] == 1
    assert results[1]["exists"] is True
    assert results[1]["valid"] is False
    assert results[2]["exists"] is False


def test_change_password_verifies_old_password_and_clears_old_backups(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="Current")])

    storage.save(vault, "old-pass")
    backup_path = tmp_path / "vault.passguard.bak1"
    backup_path.write_bytes(vault_path.read_bytes())

    storage.change_password(vault, "old-pass", "new-pass")

    assert storage.load("new-pass").entries[0].title == "Current"
    with pytest.raises(ValueError):
        storage.load("old-pass")
    assert not backup_path.exists()


def test_change_password_wrong_old_password_does_not_overwrite(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="Current")])

    storage.save(vault, "old-pass")
    original_payload = vault_path.read_bytes()

    with pytest.raises(ValueError):
        storage.change_password(vault, "wrong-pass", "new-pass")

    assert vault_path.read_bytes() == original_payload
    assert storage.load("old-pass").entries[0].title == "Current"


def test_save_without_backups_does_not_clear_backups_before_failed_write(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    storage = make_storage(vault_path)
    vault = Vault(entries=[Entry(title="Current")])

    storage.save(vault, "master")
    backup_path = tmp_path / "vault.passguard.bak1"
    backup_path.write_bytes(vault_path.read_bytes())

    def fail_write(payload):
        raise OSError("disk full")

    storage._atomic_write = fail_write

    with pytest.raises(OSError):
        storage.save(vault, "new-master", keep_backups=False)

    assert backup_path.exists()


def test_import_valid_vault_replaces_current_vault(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "import.passguard"
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
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "import.passguard"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="ImportedPayload")]), "import-pass")

    imported_vault = storage.import_vault_payload(import_path.read_bytes(), "import-pass")

    assert imported_vault.entries[0].title == "ImportedPayload"
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    assert storage.load("import-pass").entries[0].title == "ImportedPayload"


def test_import_can_keep_current_session_password(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "import.passguard"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="Imported")]), "import-pass")

    imported_vault = storage.import_vault(str(import_path), "import-pass", vault_password="current-pass")

    assert imported_vault.entries[0].title == "Imported"
    assert storage.load("current-pass").entries[0].title == "Imported"
    with pytest.raises(ValueError):
        storage.load("import-pass")


def test_import_payload_can_keep_current_session_password(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "import.passguard"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="ImportedPayload")]), "import-pass")

    imported_vault = storage.import_vault_payload(import_path.read_bytes(), "import-pass", vault_password="current-pass")

    assert imported_vault.entries[0].title == "ImportedPayload"
    assert storage.load("current-pass").entries[0].title == "ImportedPayload"
    with pytest.raises(ValueError):
        storage.load("import-pass")


def test_import_wrong_password_does_not_overwrite_current_vault(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "import.passguard"
    storage = make_storage(vault_path)
    import_storage = make_storage(import_path)

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_storage.save(Vault(entries=[Entry(title="Imported")]), "import-pass")
    original_payload = vault_path.read_bytes()

    with pytest.raises(ValueError, match="File import"):
        storage.import_vault(str(import_path), "wrong-pass")

    assert vault_path.read_bytes() == original_payload
    assert storage.load("current-pass").entries[0].title == "Current"


def test_import_legacy_gcm_vault_reencrypts_to_argon2id(tmp_path):
    vault_path = tmp_path / "vault.passguard"
    import_path = tmp_path / "legacy_import.passguard"
    storage = make_storage(vault_path)
    legacy_vault = Vault(entries=[Entry(title="Legacy")])

    storage.save(Vault(entries=[Entry(title="Current")]), "current-pass")
    import_path.write_bytes(legacy_gcm_payload(legacy_vault, "legacy-pass"))

    imported_vault = storage.import_vault(str(import_path), "legacy-pass")

    assert imported_vault.entries[0].title == "Legacy"
    assert vault_path.read_bytes().startswith(A2G1_MAGIC)
    assert storage.load("legacy-pass").entries[0].title == "Legacy"
