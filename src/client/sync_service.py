# sandbox/client/sync_service.py
import requests
from enum import Enum
from typing import List, Optional
from src.client.database import db, LocalVaultItem
from src.client.state import state
from src.client.profile_manager import Profile

class SyncStatus(Enum):
    SYNCED = "已同步"
    LOCAL_NEW = "本地新增"
    REMOTE_NEW = "云端新增"
    LOCAL_MODIFIED = "本地修改"
    REMOTE_MODIFIED = "云端修改"
    CONFLICT = "冲突(两端均修改)"

class SyncDiffItem:
    def __init__(self, id: str, status: SyncStatus, local_item: Optional[LocalVaultItem]=None, remote_item: Optional[dict]=None):
        self.id = id
        self.status = status
        self.local_item = local_item
        self.remote_item = remote_item
        self.action = "SKIP"

class SyncService:
    def __init__(self, profile: Profile):
        self.profile = profile
        if not self.profile.server_url or not state.token:
            raise ValueError("未登录或无服务器配置")

    def check_diff(self) -> List[SyncDiffItem]:
        server_url = self.profile.server_url or ""
        if not server_url: return []
        
        current_user = state.username
        if not current_user:
            return []
        # 获取本地数据
        local_items_map = {item.id: item for item in db.get_all_items(include_deleted=True)}
        
        headers = {"Authorization": f"Bearer {state.token}"}
        try:
            api_url = f"{server_url.rstrip('/')}/api/v1/sync"
            resp = requests.post(
                api_url,
                json={"last_sync_timestamp": 0, "push_items": []}, 
                headers=headers, timeout=10
            )
            
            if resp.status_code != 200:
                print(f"[Check Diff] Error {resp.status_code}: {resp.text}")
                raise Exception(f"服务器返回错误: {resp.status_code}")
            
            remote_items_list = resp.json()["pull_items"]
            remote_items_map = {item["id"]: item for item in remote_items_list}
            
        except Exception as e:
            print(f"Check diff failed: {e}")
            raise e

        diff_list = []
        all_ids = set(local_items_map.keys()) | set(remote_items_map.keys())
        config = db.get_config()

        for pid in all_ids:
            local = local_items_map.get(pid)
            remote = remote_items_map.get(pid)

            if local and local.owner and local.owner != current_user:
                continue
            
            if local and not remote:
                diff_list.append(SyncDiffItem(pid, SyncStatus.LOCAL_NEW, local_item=local))
            
            elif remote and not local:
                diff_list.append(SyncDiffItem(pid, SyncStatus.REMOTE_NEW, remote_item=remote))
            
            elif local and remote:
                remote_ts = remote.get("updated_at", 0)
                local_sync_ts = config.last_sync_timestamp
                
                if local.is_dirty:
                    if remote_ts > local_sync_ts + 1.0:
                        diff_list.append(SyncDiffItem(pid, SyncStatus.CONFLICT, local, remote))
                    else:
                        diff_list.append(SyncDiffItem(pid, SyncStatus.LOCAL_MODIFIED, local, remote))
                elif remote_ts > local.updated_at:
                    diff_list.append(SyncDiffItem(pid, SyncStatus.REMOTE_MODIFIED, local, remote))
        
        return diff_list

    def execute_sync(self, diff_items: List[SyncDiffItem]):
        server_url = self.profile.server_url or ""
        if not server_url: return

        current_username = state.username or "unknown"
        push_list = []
        
        for item in diff_items:
            # PULL: 远程 -> 本地
            if item.action == "PULL" and item.remote_item:
                db.save_item(
                    item_id=item.remote_item["id"],
                    encrypted_data=item.remote_item["encrypted_data"],
                    is_deleted=item.remote_item["is_deleted"],
                    is_dirty=False,
                    owner=current_username 
                )
            
            # PUSH
            elif (item.action == "PUSH" or item.action == "MERGE_USE_LOCAL") and item.local_item:
                push_list.append({
                    "id": item.local_item.id,
                    "encrypted_data": item.local_item.encrypted_data,
                    "is_deleted": item.local_item.is_deleted
                })

        if push_list:
            print(f"[Sync] Pushing {len(push_list)} items...")
            
            headers = {"Authorization": f"Bearer {state.token}"}
            payload = {
                "last_sync_timestamp": db.get_config().last_sync_timestamp,
                "push_items": push_list
            }
            
            try:
                resp = requests.post(
                    f"{server_url.rstrip('/')}/api/v1/sync",
                    json=payload, headers=headers, timeout=15
                )
                
                if resp.status_code == 200:
                    # print("[Sync] Push Success!")
                    # server_ts = resp.json()["server_timestamp"]
                    # pushed_ids = [p["id"] for p in push_list]
                    
                    # db.mark_synced(pushed_ids, sync_time=server_ts, owner=current_username)
                    
                    # db.update_config(last_sync_timestamp=server_ts)
                    
                    resp_data = resp.json()
                    server_ts = resp_data["server_timestamp"]
                    succeeded_ids = resp_data.get("processed_ids", [p["id"] for p in push_list])
                    print(f"[Sync] Push Success. Requested: {len(push_list)}, Accepted: {len(succeeded_ids)}")
                    db.mark_synced(succeeded_ids, sync_time=server_ts, owner=current_username)
                    db.update_config(last_sync_timestamp=server_ts)
                else:
                    raise Exception(f"上传失败 {resp.status_code}: {resp.text}")
                    
            except Exception as e:
                print(f"[Sync Exception] {e}")
                raise e