from typing import List, Optional, ClassVar
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    __tablename__: ClassVar[str] = "users" 
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    kdf_salt: str
    created_at: datetime = Field(default_factory=datetime.now)
    items: List["VaultItem"] = Relationship(back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete"})


class VaultItem(SQLModel, table=True):
    __tablename__: ClassVar[str] = "vault_items"
    id: str = Field(primary_key=True, index=True)
    encrypted_data: str
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    is_deleted: bool = Field(default=False)
    owner_id: int = Field(foreign_key="users.id")
    owner: User = Relationship(back_populates="items")