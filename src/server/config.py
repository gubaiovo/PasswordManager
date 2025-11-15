# 数据库url等服务端配置文件
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- 基础配置 ---
    PROJECT_NAME: str = "MyCipherVault Server"
    API_V1_STR: str = "/api/v1"
    
    # --- 安全配置 (JWT) ---
    # 这是一个随机字符串，用于给登录令牌(Token)签名。
    # 绝对不能泄露！在生产环境中应该非常长且随机。
    # 默认值仅用于开发环境，不要在生产环境使用默认值！
    SECRET_KEY: str = "INSECURE_DEFAULT_KEY_PLEASE_CHANGE_ME" 
    
    # 加密算法，通常使用 HS256
    ALGORITHM: str = "HS256"
    
    # Token 过期时间 (分钟)，默认 30 天 (30 * 24 * 60)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200 

    # --- 数据库配置 ---
    # 默认使用本地 SQLite 文件，生产环境可以改为 PostgreSQL 链接
    DATABASE_URL: str = "sqlite:///./cloud_vault.db"

    # --- Pydantic 配置 ---
    # 告诉 Pydantic 去读取根目录下的 .env 文件
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# 使用 lru_cache 缓存配置，避免每次请求都重复读取文件
@lru_cache
def get_settings():
    return Settings()

# 实例化一个对象供其他模块调用
settings = get_settings()