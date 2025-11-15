# 登录接口# src/server/routers/auth.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel
from jose import JWTError, jwt

from ..database import get_session
from ..models import User
from ..security import get_password_hash, verify_password, create_access_token
from ..config import settings

router = APIRouter()

# --- 1. 定义 Pydantic 模型 (DTO) ---
# 用于请求体校验

class UserCreate(BaseModel):
    username: str
    password: str
    kdf_salt: str  # 注册时必须上传客户端生成的 Salt

class Token(BaseModel):
    access_token: str
    token_type: str

class UserRead(BaseModel):
    id: int
    username: str
    kdf_salt: str 
    
class UserCheckResponse(BaseModel):
    exists: bool
# --- 2. 核心依赖: 获取当前用户 ---
# OAuth2PasswordBearer 会自动从请求头 Authorization: Bearer <token> 中提取 token
# tokenUrl 参数指向我们下面定义的登录接口地址，用于 Swagger UI 自动测试
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user( token: Annotated[str, Depends(oauth2_scheme)],
                            session: Session = Depends(get_session)
                        ) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # --- 修改开始 ---
        # 1. 先用一个临时变量接收，允许它是 None
        username_val = payload.get("sub")
        
        # 2. 显式检查是否为 None
        if username_val is None:
            raise credentials_exception
            
        # 3. 确认非空后，强制转为 str 类型赋值给 username
        username: str = str(username_val)
        # --- 修改结束 ---
        
    except JWTError:
        raise credentials_exception
    
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user
# --- 3. API 接口 ---

@router.get("/check/{username}", response_model=UserCheckResponse)
def check_user_exists(username: str, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    return {"exists": user is not None}

@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    # 1. 检查用户名是否已存在
    statement = select(User).where(User.username == user_in.username)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Username already registered"
        )
    
    # 2. 创建新用户
    # 注意：这里存的是登录密码的哈希，和 kdf_salt
    new_user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        kdf_salt=user_in.kdf_salt
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    # 1. 查找用户
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()
    
    # 2. 验证密码 (登录密码)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. 生成 Token
    access_token = create_access_token(subject=user.username)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息 (包括 kdf_salt)
    客户端登录后需要调用此接口获取 kdf_salt，才能解密本地数据
    """
    return current_user