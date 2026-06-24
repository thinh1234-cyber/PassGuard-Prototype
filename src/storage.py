import os
from src.models import Vault
from src.crypto import VaultCrypto

import shutil

class VaultStorage:
    def __init__(self, filepath="vault.luupass"):
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
        else:
            self._clear_backups()
        self._atomic_write(encrypted_payload)

    def validate_import_file(self, import_path: str, password: str) -> Vault:
        if not os.path.exists(import_path):
            raise ValueError("File vault import không tồn tại.")

        try:
            return self._load_from_file(import_path, password)
        except Exception as e:
            raise ValueError("File import không hợp lệ hoặc mật khẩu import sai.") from e

    def import_vault(self, import_path: str, password: str) -> Vault:
        imported_vault = self.validate_import_file(import_path, password)
        self.save(imported_vault, password, keep_backups=False)
        return imported_vault

    def load(self, password: str) -> Vault:
        backup_paths = [f"{self.filepath}.bak{i}" for i in range(1, 4)]
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
