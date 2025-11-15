import flet as ft
import requests
import json
import uuid
from typing import Optional, cast
from src.client.database import db
from src.client.state import state
from src.client.profile_manager import pm, Profile
from src.core.models import PasswordItem
from src.core.generator import generate_password

def VaultView(page: ft.Page):
    decrypted_items = [] 

    search_field = ft.TextField(
        prefix_icon="search",
        hint_text="搜索网站、用户名...",
        expand=True,
        on_change=lambda e: filter_list(e.control.value)
    )

    items_list_view = ft.ListView(expand=True, spacing=10, padding=20)

    def load_data():
        items_list_view.controls.clear()
        decrypted_items.clear()
        local_items = db.get_all_items()
        
        # current_profile = state.current_profile
        # current_user = state.username or (current_profile.username if current_profile else None)
        # print(f"Loading data for user context: {current_user}")
        
        for l_item in local_items:
            # if l_item.owner and l_item.owner != current_user:
            #     continue
            try:
                p_item = state.crypto.decrypt_item(l_item.encrypted_data)
                p_item.id = uuid.UUID(l_item.id) 
                decrypted_items.append(p_item)
            except Exception as e:
                print(f"解密失败 ID {l_item.id}: {e}")
        render_list(decrypted_items)

    def render_list(items):
        items_list_view.controls.clear()
        if not items:
            items_list_view.controls.append(
                ft.Text("暂无数据，请点击右下角添加", text_align=ft.TextAlign.CENTER, color="grey")
            )
        
        for item in items:
            def delete_action(e, item_id=item.id):
                delete_item(item_id)
            def edit_action(e, item_obj=item):
                show_edit_dialog(item_obj)

            # 获取本地y元数据
            local_raw = db.get_item(str(item.id))
            
            # 副标题 用户名 + 同步状态
            subtitle_controls = [
                ft.Text(item.username, size=12, color="grey")
            ]
            
            # 如果有 Owner，显示绿色标签
            if local_raw and local_raw.owner:
                subtitle_controls.append(
                    ft.Container(
                        content=ft.Text(f"已同步: {local_raw.owner}", size=10, color="white"),
                        bgcolor="green",
                        padding=ft.padding.symmetric(horizontal=4, vertical=1),
                        border_radius=4
                    )
                )
            elif local_raw and local_raw.is_dirty:
                subtitle_controls.append(
                    ft.Container(
                        content=ft.Text("未同步修改", size=10, color="white"),
                        bgcolor="orange",
                        padding=ft.padding.symmetric(horizontal=4, vertical=1),
                        border_radius=4
                    )
                )

            list_tile = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(name="lock", size=30, color="blue"),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(item.title, weight=ft.FontWeight.BOLD, size=16),
                                    # 副标题行
                                    ft.Row(subtitle_controls, spacing=5)
                                ], expand=True, spacing=2
                            ),
                            expand=True, on_click=edit_action,
                        ),
                        ft.IconButton(icon="copy", tooltip="复制密码", on_click=lambda e, p=item.password: copy_to_clipboard(p)),
                        ft.IconButton(icon="delete", tooltip="删除", icon_color="red", on_click=delete_action),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                padding=10, border=ft.border.all(1, "grey300"), border_radius=10, bgcolor="white",
            )
            items_list_view.controls.append(list_tile)
        page.update()

    def filter_list(query: str):
        if not query:
            render_list(decrypted_items)
            return
        query = query.lower()
        filtered = [item for item in decrypted_items if query in item.title.lower() or query in item.username.lower() or (item.url and query in item.url.lower())]
        render_list(filtered)

    def copy_to_clipboard(password: str):
        page.set_clipboard(password)
        page.open(ft.SnackBar(ft.Text("密码已复制到剪贴板!")))

    def logout(e):
        state.clear()
        page.go("/login")

    # --- 删除逻辑 ---
    def delete_item(item_id: uuid.UUID):
        def confirm_del(e):
            try:
                local_item = db.get_item(str(item_id))
                if local_item:
                    db.save_item(
                        item_id=str(item_id),
                        encrypted_data=local_item.encrypted_data,
                        is_deleted=True, 
                        is_dirty=True
                    )
                    page.close(confirm_dlg)
                    page.open(ft.SnackBar(ft.Text("已删除")))
                    load_data()
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"删除失败: {ex}")))

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text("确定要删除这条密码吗？此操作将在下次同步时从云端移除。"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(confirm_dlg)),
                ft.ElevatedButton("删除", color="white", bgcolor="red", on_click=confirm_del),
            ],
        )
        page.open(confirm_dlg)

    # --- 账号管理 ---
    def show_account_dialog(e):
        current_profile = cast(Optional[Profile], state.current_profile)
        if not current_profile: return

        # 判断是否在线 (有 Token)
        is_online = state.token is not None
        
        # 显示的用户名：优先取内存(已登录)，其次取档案记录(未登录)
        display_name = state.username or current_profile.username or "未设置账号"
        server_url = current_profile.server_url or "未设置"

        def handle_server_logout(e):
            state.token = None
            state.username = None
            # 彻底忘记
            # if current_profile:
            #     current_profile.username = None
            #     pm.update_profile(current_profile.name, username=None)
            account_btn.icon_color = "grey"
            account_btn.update()
            
            page.close(account_dlg)
            page.open(ft.SnackBar(ft.Text("已断开服务器连接")))
            page.update() 

        def handle_login_click(e):
            page.close(account_dlg)
            show_server_login_dialog()

        if is_online:
            # --- 已登录状态 ---
            status_row = ft.Row([
                ft.Icon("check_circle", color="green", size=16),
                ft.Text("状态: 已连接", color="green")
            ])
            action_btn = ft.ElevatedButton(
                "断开连接 / 退出", 
                on_click=handle_server_logout, 
                color="red", 
                bgcolor="white"
            )
        else:
            # --- 未登录状态 ---
            status_row = ft.Row([
                ft.Icon("error_outline", color="orange", size=16),
                ft.Text("状态: 未连接 (点击登录)", color="orange")
            ])
            action_btn = ft.ElevatedButton(
                "立即登录", 
                on_click=handle_login_click, 
                bgcolor="blue", 
                color="white"
            )

        account_dlg = ft.AlertDialog(
            title=ft.Text("账号信息"),
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(name="person", color="blue" if is_online else "grey"),
                    title=ft.Text(display_name, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"服务器: {server_url}"),
                ),
                status_row,
                ft.Divider(),
                ft.Text("提示：重启应用后需要重新验证身份。", size=12, color="grey")
            ], tight=True, width=350),
            actions=[
                ft.TextButton("关闭", on_click=lambda e: page.close(account_dlg)),
                action_btn,
            ],
        )
        page.open(account_dlg)

    def show_server_login_dialog():
        current_profile = cast(Optional[Profile], state.current_profile)
        
        if not current_profile or not current_profile.server_url:
            page.open(ft.SnackBar(ft.Text("错误：当前档案未配置服务器地址，请先在登录页编辑档案。")))
            return

        user_tf = ft.TextField(label="用户名", value=current_profile.username or "")
        pass_tf = ft.TextField(label="密码", password=True, can_reveal_password=True)
        
        base_url = current_profile.server_url.rstrip('/')

        # 登录
        def perform_login(username, password):
            token_url = f"{base_url}/auth/token"
            # 登录请求
            resp = requests.post(token_url, data={"username": username, "password": password})
            
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                
                # 更新内存状态
                state.token = token
                state.username = username
                
                # 更新并保存本地信息
                current_profile.username = username
                pm.update_profile(current_profile.name, username=username)
                
                page.close(login_dlg)
                page.open(ft.SnackBar(ft.Text("登录成功")))
                
                # 登录成功后跳转到同步中心
                page.go("/sync_center")
            else:
                page.open(ft.SnackBar(ft.Text(f"登录失败: {resp.text}")))

        # 注册、自动登录
        def perform_register(username, password, confirm_dlg):
            config = db.get_config()
            # 确认本地 Salt
            if not config.kdf_salt:
                page.open(ft.SnackBar(ft.Text("本地未初始化，无法注册")))
                return

            reg_url = f"{base_url}/auth/register"
            try:
                resp = requests.post(reg_url, json={
                    "username": username,
                    "password": password,
                    "kdf_salt": config.kdf_salt
                })
                if resp.status_code == 200:
                    page.close(confirm_dlg) # 关闭确认弹窗
                    page.open(ft.SnackBar(ft.Text("注册成功，正在登录...")))
                    # 注册成功后，自动登录
                    perform_login(username, password)
                else:
                    page.open(ft.SnackBar(ft.Text(f"注册失败: {resp.text}")))
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"连接错误: {ex}")))

        # 3. 是否创建新用户
        def show_create_confirm(username, password):
            def on_yes(e):
                perform_register(username, password, confirm_dlg)
            
            confirm_dlg = ft.AlertDialog(
                title=ft.Text("用户不存在"),
                content=ft.Text(f"服务器上未找到用户 '{username}'。\n是否立即创建新账号并登录？"),
                actions=[
                    ft.TextButton("取消", on_click=lambda e: page.close(confirm_dlg)),
                    ft.ElevatedButton("创建并登录", on_click=on_yes),
                ],
            )
            page.open(confirm_dlg)

        # 4. 连接
        def handle_connect(e):
            user_val = user_tf.value or ""
            pass_val = pass_tf.value or ""
            
            if not user_val or not pass_val:
                page.open(ft.SnackBar(ft.Text("请输入账号密码")))
                return

            try:
                # 检查用户是否存在
                check_url = f"{base_url}/auth/check/{user_val}"
                resp = requests.get(check_url, timeout=5)
                
                if resp.status_code == 200:
                    exists = resp.json().get("exists", False)
                    if not exists:
                        # 用户不存在 -> 弹窗询问是否注册
                        show_create_confirm(user_val, pass_val)
                    else:
                        # 用户存在 -> 直接登录
                        perform_login(user_val, pass_val)
                else:
                    # 如果 check 报错，回退到直接尝试登录
                    perform_login(user_val, pass_val)
            
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"连接错误: {ex}")))

        # 手动跳转注册页
        def go_to_register(dlg):
            page.close(dlg)
            page.go("/register")

        login_dlg = ft.AlertDialog(
            title=ft.Text("连接服务器"),
            content=ft.Column([
                ft.Text(f"地址: {current_profile.server_url}"),
                user_tf,
                pass_tf,
                ft.Text("提示：如果用户不存在，将自动提示创建。", size=12, color="grey")
            ], tight=True, width=350),
            actions=[
                ft.TextButton("手动注册", on_click=lambda e: go_to_register(login_dlg)),
                ft.TextButton("取消", on_click=lambda e: page.close(login_dlg)),
                ft.ElevatedButton("连接 / 登录", on_click=handle_connect),
            ],
        )
        page.open(login_dlg)
        
    def go_to_sync_center(e):
        if not state.token:
            show_server_login_dialog()
            return
        page.go("/sync_center")

    # 新增/编辑 弹窗
    def show_edit_dialog(item: Optional[PasswordItem] = None):
        is_edit = item is not None
        title_tf = ft.TextField(label="标题", value=item.title if is_edit else "")
        username_tf = ft.TextField(label="用户名", value=item.username if is_edit else "")
        password_tf = ft.TextField(label="密码", can_reveal_password=True, value=item.password if is_edit else "")
        url_tf = ft.TextField(label="网址", value=item.url if is_edit else "")
        
        def generate_random_pwd(e):
            pwd = generate_password(length=16)
            password_tf.value = pwd
            password_tf.update()

        def save_item(e):
            title_val = title_tf.value or ""
            pwd_val = password_tf.value or ""
            if not title_val or not pwd_val: return
            try:
                new_id = item.id if item else uuid.uuid4()
                new_item_obj = PasswordItem(
                    id=new_id,
                    title=title_val,
                    username=username_tf.value or "",
                    password=pwd_val,
                    url=url_tf.value or ""
                )
                encrypted_blob = state.crypto.encrypt_item(new_item_obj)
                db.save_item(item_id=str(new_id), encrypted_data=encrypted_blob, is_dirty=True)
                page.close(dlg)
                load_data()
                page.open(ft.SnackBar(ft.Text("保存成功")))
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"保存失败: {ex}")))

        dlg = ft.AlertDialog(
            title=ft.Text("编辑密码" if is_edit else "添加新密码"),
            content=ft.Column([
                title_tf, 
                username_tf, 
                ft.Row(
                    [
                        password_tf, 
                        ft.IconButton(icon="refresh", tooltip="随机", on_click=generate_random_pwd)
                    ], 
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ), 
                url_tf
            ], tight=True, width=400),
            actions=[ft.TextButton("取消", on_click=lambda e: page.close(dlg)), ft.ElevatedButton("保存", on_click=save_item)],
        )
        page.open(dlg)

    load_data()
    account_btn = ft.IconButton(
        icon="account_circle", 
        icon_color="blue" if state.token else "grey", 
        tooltip="账号管理", 
        on_click=show_account_dialog
    )
    
    return ft.View(
        "/vault",
        controls=[
            ft.AppBar(
                title=ft.Text("我的密码"),
                bgcolor="surfaceVariant",
                actions=[
                    ft.IconButton(icon="sync", tooltip="同步中心", on_click=go_to_sync_center),
                    account_btn,
                    ft.IconButton(icon="lock", tooltip="锁定PasswordManger", on_click=logout),
                ]
            ),
            ft.Container(search_field, padding=10),
            items_list_view,
        ],
        floating_action_button=ft.FloatingActionButton(
            icon="add",
            on_click=lambda e: show_edit_dialog(None),
            text="添加"
        )
    )