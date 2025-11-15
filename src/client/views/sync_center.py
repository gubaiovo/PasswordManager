# sandbox/client/views/sync_center.py
import flet as ft
from typing import cast
from src.client.state import state
from src.client.sync_service import SyncService, SyncStatus, SyncDiffItem
from src.client.profile_manager import Profile

def SyncCenterView(page: ft.Page):
    raw_profile = state.current_profile
    if not raw_profile:
        return ft.View("/sync_center", controls=[ft.Text("错误：未找到当前档案信息", color="red")])
    current_profile = cast(Profile, raw_profile)
    try:
        service = SyncService(current_profile)
    except Exception as e:
        return ft.View("/sync_center", controls=[ft.Text(f"初始化失败: {e}", color="red")])

    diff_items: list[SyncDiffItem] = []
    
    status_text = ft.Text("正在检查差异...", color="blue")
    diff_list_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    action_btn = ft.ElevatedButton(
        "执行同步", 
        icon="cloud_sync", 
        on_click=lambda e: execute_sync(),
        disabled=True
    )

    # --- 批量操作 ---
    def batch_set_action(action_type: str):
        count = 0
        for item in diff_items:
            if item.status != SyncStatus.CONFLICT:
                if action_type == "PUSH" and (item.status in [SyncStatus.LOCAL_NEW, SyncStatus.LOCAL_MODIFIED]):
                    item.action = "PUSH"
                    count += 1
                elif action_type == "PULL" and (item.status in [SyncStatus.REMOTE_NEW, SyncStatus.REMOTE_MODIFIED]):
                    item.action = "PULL"
                    count += 1
                elif action_type == "SKIP":
                    item.action = "SKIP"
                    count += 1
        
        render_list()
        page.open(ft.SnackBar(ft.Text(f"已批量设置 {count} 项为 {action_type}")))

    batch_actions_row = ft.Row([
        ft.Text("批量操作:", weight=ft.FontWeight.BOLD),
        ft.TextButton("全部上传 (Local->Cloud)", on_click=lambda e: batch_set_action("PUSH")),
        ft.TextButton("全部下载 (Cloud->Local)", on_click=lambda e: batch_set_action("PULL")),
        ft.TextButton("全部忽略", on_click=lambda e: batch_set_action("SKIP")),
    ], visible=False) 
    
    def load_diffs():
        status_text.value = "正在连接服务器比对数据..."
        diff_list_col.controls.clear() # 清空列表
        page.update()
        
        try:
            diffs = service.check_diff()
            diff_items.clear()
            diff_items.extend(diffs)
            
            render_list()
            
            if not diffs:
                status_text.value = "本地与云端数据一致，无需同步。"
                status_text.color = "green"
                batch_actions_row.visible = False
                action_btn.disabled = True
            else:
                status_text.value = f"发现 {len(diffs)} 项差异，请确认操作："
                status_text.color = "black"
                batch_actions_row.visible = True
                action_btn.disabled = False
            
            page.update()
            
        except Exception as e:
            status_text.value = f"检查失败: {e}"
            status_text.color = "red"
            page.update()

    def get_item_title(item: SyncDiffItem) -> str:
        try:
            target_data = ""
            if item.local_item:
                target_data = item.local_item.encrypted_data
            elif item.remote_item:
                target_data = item.remote_item["encrypted_data"]
            else:
                return "未知数据"
            p_item = state.crypto.decrypt_item(target_data)
            return f"{p_item.title} ({p_item.username})"
        except:
            return f"加密数据 ({item.id[:8]}...)"

    def render_list():
        diff_list_col.controls.clear()
        
        for item in diff_items:
            icon_name = "help"
            icon_color = "grey"
            status_str = item.status.value
            options = []

   
            if item.status == SyncStatus.LOCAL_NEW:
                icon_name = "upload"; icon_color = "green"; 
                if item.action == "SKIP": item.action = "PUSH" 
                options = [ft.dropdown.Option("PUSH", "上传"), ft.dropdown.Option("SKIP", "忽略")]
            elif item.status == SyncStatus.REMOTE_NEW:
                icon_name = "download"; icon_color = "blue"; 
                if item.action == "SKIP": item.action = "PULL"
                options = [ft.dropdown.Option("PULL", "下载"), ft.dropdown.Option("SKIP", "忽略")]
            elif item.status == SyncStatus.LOCAL_MODIFIED:
                icon_name = "upload_file"; icon_color = "orange"; 
                if item.action == "SKIP": item.action = "PUSH"
                options = [ft.dropdown.Option("PUSH", "覆盖云端"), ft.dropdown.Option("PULL", "还原"), ft.dropdown.Option("SKIP", "忽略")]
            elif item.status == SyncStatus.REMOTE_MODIFIED:
                icon_name = "download_done"; icon_color = "teal"; 
                if item.action == "SKIP": item.action = "PULL"
                options = [ft.dropdown.Option("PULL", "更新本地"), ft.dropdown.Option("PUSH", "强制覆盖"), ft.dropdown.Option("SKIP", "忽略")]
            elif item.status == SyncStatus.CONFLICT:
                icon_name = "warning"; icon_color = "red"; 
                item.action = "SKIP" 
                options = [ft.dropdown.Option("SKIP", "请选择..."), ft.dropdown.Option("PUSH", "保留本地"), ft.dropdown.Option("PULL", "保留云端")]

            def on_action_change(e, diff_item=item):
                diff_item.action = e.control.value

            dd = ft.Dropdown(
                width=140, text_size=12, value=item.action, options=options, on_change=on_action_change, content_padding=5
            )

            row = ft.Container(
                content=ft.Row([
                    ft.Icon(icon_name, color=icon_color),
                    ft.Column([
                        ft.Text(get_item_title(item), weight=ft.FontWeight.BOLD),
                        ft.Text(status_str, size=12, color="grey")
                    ], expand=True),
                    dd
                ]),
                padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, "grey200"))
            )
            diff_list_col.controls.append(row)
        
        page.update()

    def execute_sync():
        action_btn.disabled = True
        action_btn.text = "同步中..."
        page.update()
        try:
            service.execute_sync(diff_items)
            page.open(ft.SnackBar(ft.Text("同步执行完毕")))
            load_diffs()
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"同步错误: {e}")))
        finally:
            action_btn.disabled = False
            action_btn.text = "执行同步"
            page.update()

    load_diffs()

    return ft.View(
        "/sync_center",
        controls=[
            ft.AppBar(
                title=ft.Text("同步差异对比"),
                bgcolor="surfaceVariant",
                leading=ft.IconButton(icon="arrow_back", on_click=lambda _: page.go("/vault"))
            ),
            ft.Container(content=status_text, padding=10, bgcolor="blue50"),
            ft.Container(content=batch_actions_row, padding=5),
            diff_list_col,
            ft.Container(content=action_btn, padding=20, alignment=ft.alignment.center)
        ]
    )