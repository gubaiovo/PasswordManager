from typing import Optional
from src.core.crypto import CryptoManager

class AppState:
    def __init__(self):
        self.crypto = CryptoManager()
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        
        self.current_profile: Optional[object] = None

    @property
    def is_vault_unlocked(self) -> bool:
        return self.crypto._key is not None

    @property
    def is_server_authenticated(self) -> bool:
        return self.token is not None

    def clear(self):
        self.crypto = CryptoManager() 
        self.token = None
        self.username = None
        self.current_profile = None

state = AppState()