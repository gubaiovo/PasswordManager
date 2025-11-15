# sandbox/server/routers/sync.py
from typing import List
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel

from ..database import get_session
from ..models import VaultItem, User
from .auth import get_current_user

router = APIRouter()

class VaultItemPush(BaseModel):
    id: str
    encrypted_data: str
    is_deleted: bool

class SyncRequest(BaseModel):
    last_sync_timestamp: float = 0.0
    push_items: List[VaultItemPush] 

class SyncResponse(BaseModel):
    server_timestamp: float
    pull_items: List[VaultItem]
    processed_ids: List[str] = []
    
@router.post("/sync", response_model=SyncResponse)
def sync_vault(
    payload: SyncRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user_id: int = current_user.id # type: ignore
    current_time = time.time()
    
    print(f"\n>>> [Sync Request] User: {current_user.username} (ID: {user_id})")
    print(f">>> Payload: {len(payload.push_items)} items to PUSH")
    processed_ids = []
    # 1. PUSH 处理
    processed_count = 0
    skipped_count = 0
    
    for item_in in payload.push_items:
        db_item = session.get(VaultItem, item_in.id)
        
        if db_item:
            # [诊断重点] 检查所有权
            if db_item.owner_id != user_id:
                print(f"!!! [SKIP] ID冲突/无权修改: {item_in.id} (Owner: {db_item.owner_id} != Current: {user_id})")
                skipped_count += 1
                continue 
            
            # 更新逻辑
            db_item.encrypted_data = item_in.encrypted_data
            db_item.is_deleted = item_in.is_deleted
            db_item.updated_at = current_time
            print(f"    [UPDATE] {item_in.id}")
            processed_count += 1
            processed_ids.append(item_in.id)
        else:
            # 新增逻辑
            print(f"    [INSERT] {item_in.id}")
            new_item = VaultItem(
                id=item_in.id,
                encrypted_data=item_in.encrypted_data,
                is_deleted=item_in.is_deleted,
                updated_at=current_time,
                owner_id=user_id
            )
            session.add(new_item)
            processed_count += 1
            processed_ids.append(item_in.id)
    
    try:
        session.commit()
        print(f">>> [COMMIT] Success. Processed: {processed_count}, Skipped: {skipped_count}")
    except Exception as e:
        print(f"!!! [COMMIT ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 2. PULL 处理
    statement = select(VaultItem).where(
        VaultItem.owner_id == user_id,
        VaultItem.updated_at > payload.last_sync_timestamp
    )
    server_items = session.exec(statement).all()
    
    print(f">>> [PULL] Returning {len(server_items)} items to client.\n")

    return SyncResponse(
        server_timestamp=current_time,
        pull_items=list(server_items),
        processed_ids=processed_ids
    )