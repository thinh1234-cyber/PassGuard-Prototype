import os
import pytest
from src.storage import VaultStorage
from src.models import Vault, Entry

def test_save_and_load_vault(tmp_path):
    vault_path = tmp_path / "vault.luupass"
    storage = VaultStorage(str(vault_path))
    vault = Vault(entries=[Entry(title="T", username="U", password="P")])
    
    storage.save(vault, "master")
    assert os.path.exists(vault_path)
    
    loaded_vault = storage.load("master")
    assert loaded_vault.entries[0].title == "T"
