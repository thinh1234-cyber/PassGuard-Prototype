import pytest
from src.models import Entry, Vault, Account

def test_entry_creation():
    entry = Entry(title="Test", accounts=[Account(username="user", password="123")])
    assert entry.title == "Test"
    assert entry.url == ""

def test_vault_serialization():
    vault = Vault(entries=[Entry(title="Test", accounts=[Account(username="u", password="p")])])
    json_data = vault.model_dump_json()
    assert "Test" in json_data
