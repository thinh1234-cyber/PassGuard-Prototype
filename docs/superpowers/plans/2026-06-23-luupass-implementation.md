# LuuPass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight, simple password manager with local AES-256 encryption using Flet, exportable to Windows (.exe) and Android (.apk).

**Architecture:** A single-file encrypted JSON vault managed by Pydantic models and Fernet encryption. The UI is built with Flet, utilizing a responsive layout for cross-platform support.

**Tech Stack:** Python 3, Flet, cryptography, pydantic, pytest.

---

### Task 1: Project Setup & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `src/__init__.py`

- [ ] **Step 1: Write requirements.txt**
```text
flet==0.22.1
cryptography==42.0.5
pydantic==2.6.4
pytest==8.1.1
```

- [ ] **Step 2: Install dependencies (Manually run this during execution)**
```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Commit**
```bash
git init
git add requirements.txt
git commit -m "chore: initial project setup and requirements"
```

### Task 2: Core Data Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_models.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**
```python
# src/models.py
from pydantic import BaseModel, Field
from typing import List
import uuid

class Entry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    username: str
    password: str
    url: str = ""
    notes: str = ""

class Vault(BaseModel):
    entries: List[Entry] = []
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/models.py tests/test_models.py src/__init__.py tests/__init__.py
git commit -m "feat: implement pydantic models for vault entries"
```

### Task 3: Cryptography Service

**Files:**
- Create: `src/crypto.py`
- Create: `tests/test_crypto.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_crypto.py
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_crypto.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
```python
# src/crypto.py
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

class VaultCrypto:
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data: bytes, password: str) -> tuple[bytes, bytes]:
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted_data = f.encrypt(data)
        return salt, encrypted_data

    def decrypt(self, encrypted_data: bytes, password: str, salt: bytes) -> bytes:
        key = self._derive_key(password, salt)
        f = Fernet(key)
        try:
            return f.decrypt(encrypted_data)
        except Exception as e:
            raise ValueError("Invalid password or corrupted data") from e
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_crypto.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/crypto.py tests/test_crypto.py
git commit -m "feat: implement AES-256 encryption service"
```

### Task 4: File Storage Service

**Files:**
- Create: `src/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_storage.py
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_storage.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
```python
# src/storage.py
import os
from src.models import Vault
from src.crypto import VaultCrypto

class VaultStorage:
    def __init__(self, filepath: str = "vault.luupass"):
        self.filepath = filepath
        self.crypto = VaultCrypto()

    def save(self, vault: Vault, password: str):
        data = vault.model_dump_json().encode('utf-8')
        salt, encrypted_data = self.crypto.encrypt(data, password)
        with open(self.filepath, 'wb') as f:
            f.write(salt + encrypted_data)

    def load(self, password: str) -> Vault:
        if not os.path.exists(self.filepath):
            return Vault()
        with open(self.filepath, 'rb') as f:
            content = f.read()
        if not content:
            return Vault()
        salt = content[:16]
        encrypted_data = content[16:]
        try:
            decrypted_data = self.crypto.decrypt(encrypted_data, password, salt)
            return Vault.model_validate_json(decrypted_data.decode('utf-8'))
        except Exception as e:
            raise ValueError("Failed to unlock vault") from e
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat: implement encrypted file storage logic"
```

### Task 5: Basic App Entry & Build Scripts

**Files:**
- Create: `main.py`
- Create: `build.ps1`

- [ ] **Step 1: Create UI scaffold**
```python
# main.py
import flet as ft
from src.storage import VaultStorage

def main(page: ft.Page):
    page.title = "LuuPass"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    storage = VaultStorage()

    def unlock_clicked(e):
        try:
            vault = storage.load(password_input.value)
            page.snack_bar = ft.SnackBar(ft.Text(f"Unlocked! Entries: {len(vault.entries)}"))
            page.snack_bar.open = True
            page.update()
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text("Wrong Password!"), bgcolor=ft.colors.ERROR)
            page.snack_bar.open = True
            page.update()

    password_input = ft.TextField(label="Master Password", password=True, can_reveal_password=True, width=300)
    page.add(
        ft.Column(
            [
                ft.Text("LuuPass Vault", size=30, weight=ft.FontWeight.BOLD), 
                password_input, 
                ft.ElevatedButton("Unlock", on_click=unlock_clicked)
            ],
            alignment=ft.MainAxisAlignment.CENTER, 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
```

- [ ] **Step 2: Create Build Script**
```powershell
# build.ps1
param (
    [switch]$Windows,
    [switch]$Android
)

if ($Windows) {
    Write-Host "Building Windows Executable..."
    # 'flet pack' packages the python script into an exe
    flet pack main.py --name LuuPass
}

if ($Android) {
    Write-Host "Building Android APK..."
    Write-Host "Make sure Flutter SDK and Android SDK are installed locally!"
    flet build apk --project LuuPass --module-name main
}

if (-Not $Windows -and -Not $Android) {
    Write-Host "Please specify -Windows or -Android flag"
}
```

- [ ] **Step 3: Commit**
```bash
git add main.py build.ps1
git commit -m "feat: app entry point and build scripts"
```
