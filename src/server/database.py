# src/server/database.py
from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
from .config import settings

# 1. 配置连接参数
# SQLite 需要特殊配置 check_same_thread=False，
# 因为 FastAPI 是多线程/异步的，而 SQLite 默认只允许单线程访问同一个连接。
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# 2. 创建引擎 (Engine)
# echo=True 会在控制台打印出生成的 SQL 语句，非常有助于开发和调试。
# 生产环境建议设置为 False。
engine = create_engine(
    settings.DATABASE_URL, 
    echo=True, 
    connect_args=connect_args
)

# 3. 初始化数据库函数
# 这个函数会在 main.py 启动时被调用，用于自动创建表结构
def init_db():
    # SQLModel 会自动扫描所有继承自 SQLModel 的类，并创建对应的表
    # 注意：在使用此函数前，必须在 main.py 中导入所有的 models
    SQLModel.metadata.create_all(engine)

# 4. 获取数据库会话 (Dependency)
# 这是一个生成器函数，专门配合 FastAPI 的 Depends 使用
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        # 这里的代码会在请求处理完成后执行 (即使发生异常)
        # Session 会自动关闭，连接放回连接池