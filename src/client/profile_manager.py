# sandbox/client/profile_manager.py
import json
import os
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

def get_app_data_path():
    app_name = "PasswordManager"
    home = Path.home()
    
    if sys.platform == "win32":
        # Windows: C:\Users\Name\AppData\Roaming\MyPasswordManager
        path = home / "AppData" / "Roaming" / app_name
    else:
        # Linux/Mac: /home/name/.local/share/MyPasswordManager
        path = home / ".local" / "share" / app_name
    
    path.mkdir(parents=True, exist_ok=True)
    return path

DATA_DIR = get_app_data_path()
PROFILES_FILE = str(DATA_DIR / "profiles.json")

class Profile(BaseModel):
    name: str
    db_filename: str
    server_url: Optional[str] = None
    username: Optional[str] = None

class ProfileManager:
    def __init__(self):
        self.profiles: List[Profile] = []
        self.load_profiles()

    def load_profiles(self):
        if not os.path.exists(PROFILES_FILE):
            default_db = str(DATA_DIR / "offline.db")
            self.profiles = [
                Profile(name="本地离线账户", db_filename=default_db, server_url=None, username=None)
            ]
            self.save_profiles()
        else:
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.profiles = [Profile(**p) for p in data]
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.profiles = []
        
        if not self.profiles:
            self.add_profile("本地离线账户", None, None)

    def save_profiles(self):
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            data = [p.model_dump() for p in self.profiles]
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_profile(self, name: str, server_url: Optional[str] = None, username: Optional[str] = None) -> Profile:
        if username:
            safe_name = "".join([c for c in username if c.isalnum()])
            filename = f"user_{safe_name}.db"
        else:
            filename = "offline.db"
        
        db_path = DATA_DIR / filename
            
        counter = 1
        original_path = db_path
        while any(p.db_filename == str(db_path) for p in self.profiles):
            stem = original_path.stem
            suffix = original_path.suffix 
            db_path = DATA_DIR / f"{stem}_{counter}{suffix}"
            counter += 1

        new_profile = Profile(
            name=name,
            db_filename=str(db_path),
            server_url=server_url,
            username=username
        )
        self.profiles.append(new_profile)
        self.save_profiles()
        return new_profile

    def delete_profile(self, name: str) -> bool:
        target = None
        for p in self.profiles:
            if p.name == name:
                target = p
                break
        
        if target:
            self.profiles.remove(target)
            self.save_profiles()

            if os.path.exists(target.db_filename):
                try:
                    os.remove(target.db_filename)
                except Exception:
                    pass

            if not self.profiles:
                self.add_profile("本地离线账户", None, None)
            return True
        return False

    def get_profile_by_name(self, name: str) -> Optional[Profile]:
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    def update_profile(self, name: str, **kwargs):
        target = self.get_profile_by_name(name)
        if target:
            for key, value in kwargs.items():
                if hasattr(target, key):
                    setattr(target, key, value)
            self.save_profiles()
            return target
        return None

pm = ProfileManager()