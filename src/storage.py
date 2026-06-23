import os
from src.models import Vault
from src.crypto import VaultCrypto

class VaultStorage:
    def __init__(self, filepath: str = "vault.luupass"):
        self.filepath = filepath
        self.crypto = VaultCrypto()

    def save(self, vault: Vault, password: str):
        data = vault.model_dump_json().encode('utf-8')
        encrypted_payload = self.crypto.encrypt(data, password)
        
        tmp_filepath = self.filepath + ".tmp"
        with open(tmp_filepath, 'wb') as f:
            f.write(encrypted_payload)
        
        os.replace(tmp_filepath, self.filepath)

    def load(self, password: str) -> Vault:
        if not os.path.exists(self.filepath):
            return Vault()
        with open(self.filepath, 'rb') as f:
            content = f.read()
        if not content:
            return Vault()
        try:
            decrypted_data = self.crypto.decrypt(content, password)
            return Vault.model_validate_json(decrypted_data.decode('utf-8'))
        except Exception as e:
            raise ValueError("Failed to unlock vault") from e
