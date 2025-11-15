from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

class PasswordItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    username: str
    password: str
    url: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True

class EncryptedVaultItem(BaseModel):
    id: str
    data: str
    nonce: str | None = None
    updated_at_ts: float
    
class LocalConfig(BaseModel):
    salt: str
    server_url: str | None = None
    username: str | None = None
    