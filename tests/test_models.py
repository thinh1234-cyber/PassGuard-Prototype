import pytest
from src.models import Entry, Vault

def test_entry_creation():
    entry = Entry(title="Test", username="user", password="123")
    assert entry.title == "Test"
    assert entry.url == ""

def test_vault_serialization():
    vault = Vault(entries=[Entry(title="Test", username="u", password="p")])
    json_data = vault.model_dump_json()
    assert "Test" in json_data
