import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .models import PasswordItem

class CryptoManager:
    def __init__(self):
        self._key: bytes | None = None
        self._fernet: Fernet | None = None
        
    def generate_salt(self) -> str:
        salt = os.urandom(16)
        return base64.b64encode(salt).decode('utf-8')
    
    def derive_key(self, master_password: str, salt_b64: str) -> bool:
        try:
            salt = base64.urlsafe_b64decode(salt_b64)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32, 
                salt=salt,
                iterations=600000, 
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            self._key = key
            self._fernet = Fernet(key)
            return True
        except Exception as e:
            print(f"Key derivation failed: {e}")
            return False
        
    def encrypt_item(self, item: PasswordItem) -> str:
        if not self._fernet:
            raise ValueError("Vault is lock. Please derive key first.")
        json_data = item.model_dump_json()
        encrypted_data = self._fernet.encrypt(json_data.encode('utf-8'))
        return encrypted_data.decode('utf-8')
    
    def decrypt_item(self, encrypted_data: str) -> PasswordItem:
        if not self._fernet:
            raise ValueError("Vault is lock.")
        
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_data.encode('utf-8'))
            json_data = decrypted_bytes.decode('utf-8')
            return PasswordItem.model_validate_json(json_data)
        except InvalidToken:
            raise ValueError("Invalid Master Password or Corrupted Data")
        
    def encrypt_text(self, text: str) -> str:
        if not self._fernet:
            raise ValueError("Vault is locked")
        return self._fernet.encrypt(text.encode('utf-8')).decode('utf-8')

    def decrypt_text(self, token: str) -> str:
        if not self._fernet:
            raise ValueError("Vault is locked")
        return self._fernet.decrypt(token.encode('utf-8')).decode('utf-8')