import os
from src.models import Vault
from src.crypto import VaultCrypto

import shutil

class VaultStorage:
    def __init__(self, filepath="vault.passguard"):
        self.filepath = filepath
        self.crypto = VaultCrypto()

    def _rotate_backups(self):
        if not os.path.exists(self.filepath):
            return

        for i in range(2, 0, -1):
            old_bak = f"{self.filepath}.bak{i}"
            new_bak = f"{self.filepath}.bak{i+1}"
            if os.path.exists(old_bak):
                os.replace(old_bak, new_bak)
        shutil.copy(self.filepath, f"{self.filepath}.bak1")

    def _clear_backups(self):
        for i in range(1, 4):
            bak_path = f"{self.filepath}.bak{i}"
            if os.path.exists(bak_path):
                os.remove(bak_path)

    def backup_paths(self):
        return [f"{self.filepath}.bak{i}" for i in range(1, 4)]

    def _atomic_write(self, encrypted_payload: bytes):
        tmp_filepath = self.filepath + ".tmp"
        with open(tmp_filepath, 'wb') as f:
            f.write(encrypted_payload)

        os.replace(tmp_filepath, self.filepath)

    def _load_from_file(self, filepath: str, password: str, allow_empty: bool = False) -> Vault:
        with open(filepath, 'rb') as f:
            content = f.read()
        if not content:
            if allow_empty:
                return Vault()
            raise ValueError("File vault import đang rỗng.")

        decrypted_data = self.crypto.decrypt(content, password)
        return Vault.model_validate_json(decrypted_data.decode('utf-8'))

    def save(self, vault: Vault, password: str, keep_backups: bool = True):
        data = vault.model_dump_json().encode('utf-8')
        encrypted_payload = self.crypto.encrypt(data, password)

        # Auto Backup Rotation (Keep last 3 versions for Healing Mode)
        if keep_backups:
            self._rotate_backups()
        self._atomic_write(encrypted_payload)
        if not keep_backups:
            self._clear_backups()

    def change_password(self, vault: Vault, old_password: str, new_password: str):
        if os.path.exists(self.filepath):
            self.load(old_password)

        previous_payload = None
        if os.path.exists(self.filepath):
            with open(self.filepath, "rb") as f:
                previous_payload = f.read()

        data = vault.model_dump_json().encode("utf-8")
        encrypted_payload = self.crypto.encrypt(data, new_password)

        self._atomic_write(encrypted_payload)
        try:
            self.load(new_password)
        except Exception:
            if previous_payload is not None:
                self._atomic_write(previous_payload)
            raise

        self._clear_backups()

    def validate_import_file(self, import_path: str, password: str) -> Vault:
        if not os.path.exists(import_path):
            raise ValueError("File vault import không tồn tại.")

        try:
            return self._load_from_file(import_path, password)
        except Exception as e:
            raise ValueError("File import không hợp lệ hoặc mật khẩu import sai.") from e

    def validate_import_payload(self, payload: bytes, password: str) -> Vault:
        if not payload:
            raise ValueError("File vault import đang rỗng.")

        try:
            decrypted_data = self.crypto.decrypt(payload, password)
            return Vault.model_validate_json(decrypted_data.decode('utf-8'))
        except Exception as e:
            raise ValueError("File import không hợp lệ hoặc mật khẩu import sai.") from e

    def import_vault(self, import_path: str, password: str, vault_password: str | None = None) -> Vault:
        imported_vault = self.validate_import_file(import_path, password)
        save_password = vault_password or password
        self.save(imported_vault, save_password, keep_backups=vault_password is not None)
        return imported_vault

    def import_vault_payload(self, payload: bytes, password: str, vault_password: str | None = None) -> Vault:
        imported_vault = self.validate_import_payload(payload, password)
        save_password = vault_password or password
        self.save(imported_vault, save_password, keep_backups=vault_password is not None)
        return imported_vault

    def load(self, password: str) -> Vault:
        backup_paths = self.backup_paths()
        has_backup = any(os.path.exists(path) for path in backup_paths)

        if not os.path.exists(self.filepath) and not has_backup:
            return Vault()

        try:
            return self._load_from_file(self.filepath, password, allow_empty=True)
        except Exception as main_e:
            # Healing Mode Activation
            for bak_path in backup_paths:
                if os.path.exists(bak_path):
                    try:
                        recovered_vault = self._load_from_file(bak_path, password, allow_empty=True)
                        # Heal the corrupted main file using the healthy backup
                        shutil.copy(bak_path, self.filepath)
                        return recovered_vault
                    except Exception:
                        pass
            
            # If all fail, it's 99% a wrong password, or catastrophic corruption
            raise ValueError("Sai mật khẩu hoặc toàn bộ dữ liệu đã bị hỏng!") from main_e

    def verify_backups(self, password: str) -> list[dict]:
        results = []
        for path in self.backup_paths():
            if not os.path.exists(path):
                results.append({"path": path, "exists": False, "valid": False, "error": None})
                continue

            try:
                vault = self._load_from_file(path, password, allow_empty=False)
                results.append(
                    {
                        "path": path,
                        "exists": True,
                        "valid": True,
                        "entries": len(vault.entries),
                        "error": None,
                    }
                )
            except Exception as ex:
                results.append(
                    {
                        "path": path,
                        "exists": True,
                        "valid": False,
                        "entries": None,
                        "error": str(ex),
                    }
                )
        return results
