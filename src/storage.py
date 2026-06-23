import os
from src.models import Vault
from src.crypto import VaultCrypto

import shutil

class VaultStorage:
    def __init__(self, filepath="vault.luupass"):
        self.filepath = filepath
        self.crypto = VaultCrypto()

    def save(self, vault: Vault, password: str):
        data = vault.model_dump_json().encode('utf-8')
        encrypted_payload = self.crypto.encrypt(data, password)
        
        # Auto Backup Rotation (Keep last 3 versions for Healing Mode)
        if os.path.exists(self.filepath):
            for i in range(2, 0, -1):
                old_bak = f"{self.filepath}.bak{i}"
                new_bak = f"{self.filepath}.bak{i+1}"
                if os.path.exists(old_bak):
                    os.replace(old_bak, new_bak)
            shutil.copy(self.filepath, f"{self.filepath}.bak1")
        
        tmp_filepath = self.filepath + ".tmp"
        with open(tmp_filepath, 'wb') as f:
            f.write(encrypted_payload)
        
        os.replace(tmp_filepath, self.filepath)

    def load(self, password: str) -> Vault:
        if not os.path.exists(self.filepath):
            return Vault()
            
        def try_decrypt(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            if not content:
                return Vault()
            decrypted_data = self.crypto.decrypt(content, password)
            return Vault.model_validate_json(decrypted_data.decode('utf-8'))
            
        try:
            return try_decrypt(self.filepath)
        except Exception as main_e:
            # Healing Mode Activation
            for i in range(1, 4):
                bak_path = f"{self.filepath}.bak{i}"
                if os.path.exists(bak_path):
                    try:
                        recovered_vault = try_decrypt(bak_path)
                        # Heal the corrupted main file using the healthy backup
                        shutil.copy(bak_path, self.filepath)
                        return recovered_vault
                    except Exception:
                        pass
            
            # If all fail, it's 99% a wrong password, or catastrophic corruption
            raise ValueError("Sai mật khẩu hoặc toàn bộ dữ liệu đã bị hỏng!") from main_e
