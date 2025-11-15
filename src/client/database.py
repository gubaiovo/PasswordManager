from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pathlib import Path

# --- 1. 本地数据模型 ---

class ClientConfig(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=1, primary_key=True)
    kdf_salt: Optional[str] = None 
    validation_token: Optional[str] = None
    last_sync_timestamp: float = 0.0

class LocalVaultItem(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: str = Field(primary_key=True)
    encrypted_data: str
    is_deleted: bool = Field(default=False)
    is_dirty: bool = Field(default=False)
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    owner: Optional[str] = Field(default=None)
    
# --- 数据库管理 ---

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.current_db_name = None

    def connect(self, db_filename: str):
        self.current_db_name = db_filename
        db_path = Path(db_filename).as_posix()
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        self.init_db()
        print(f"Database switched to: {db_filename}")

    def init_db(self):
        if not self.engine: raise ValueError("DB not connected")
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            config = session.get(ClientConfig, 1)
            if not config:
                session.add(ClientConfig(id=1))
                session.commit()

    # --- 配置相关 ---
    def get_config(self) -> ClientConfig:
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            config = session.get(ClientConfig, 1)
            if config is None:
                config = ClientConfig(id=1)
                session.add(config)
                session.commit()
                session.refresh(config)
            return config

    def update_config(self, **kwargs):
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            config = session.get(ClientConfig, 1)
            if config is None:
                 config = ClientConfig(id=1)
                 session.add(config)
            
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            session.add(config)
            session.commit()
            session.refresh(config)
            return config

    # --- 密码 ---
    def save_item(self, item_id: str, encrypted_data: str, is_deleted: bool = False, is_dirty: bool = True, owner: Optional[str] = None):
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            item = session.get(LocalVaultItem, item_id)
            if not item:
                item = LocalVaultItem(
                    id=item_id, 
                    encrypted_data=encrypted_data,
                    is_deleted=is_deleted,
                    is_dirty=is_dirty,
                    owner=owner 
                )
            else:
                item.encrypted_data = encrypted_data
                item.is_deleted = is_deleted
                item.is_dirty = is_dirty
                if owner is not None:
                    item.owner = owner
            
            item.updated_at = datetime.now().timestamp()
            session.add(item)
            session.commit()

    def get_item(self, item_id: str) -> Optional[LocalVaultItem]:
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            return session.get(LocalVaultItem, item_id)

    def get_all_items(self, include_deleted=False) -> List[LocalVaultItem]:
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            statement = select(LocalVaultItem)
            if not include_deleted:
                statement = statement.where(LocalVaultItem.is_deleted == False)
            return list(session.exec(statement).all())

    def get_dirty_items(self) -> List[LocalVaultItem]:
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            statement = select(LocalVaultItem).where(LocalVaultItem.is_dirty == True)
            return list(session.exec(statement).all())

    def mark_synced(self, item_ids: List[str], sync_time: Optional[float] = None, owner: Optional[str] = None):
        if not self.engine: raise ValueError("DB not connected")
        with Session(self.engine) as session:
            for pid in item_ids:
                item = session.get(LocalVaultItem, pid)
                if item:
                    item.is_dirty = False
                    if sync_time:
                        item.updated_at = sync_time
                    if owner:
                        item.owner = owner
                    session.add(item)
            session.commit()
    
# 全局单例
db = DatabaseManager()