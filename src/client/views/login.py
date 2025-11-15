# sandbox/client/views/login.py
import flet as ft
from typing import Dict, Any, Optional 
from cryptography.fernet import InvalidToken
from src.client.database import db
from src.client.state import state
from src.client.profile_manager import pm, Profile

def LoginView(page: ft.Page):
    # --- 状态变量 ---
    current_profile_ref: Dict[str, Any] = {"value": None} 
    is_register_mode_ref = {"value": False}

    # --- UI 组件 ---
    profile_dropdown = ft.Dropdown(
        label="选择账户档案",
        width=240,
        options=[], 
    )
    
    title_text = ft.Text("", size=30, weight=ft.FontWeight.BOLD)
    sub_text = ft.Text("", color="grey", size=14)
    
    pass_field = ft.TextField(
        label="主密码", 
        password=True, 
        can_reveal_password=True, 
        width=300,
        on_submit=lambda e: handle_auth_action(e)
    )
    
    error_text = ft.Text("", color="red")
    
    action_button = ft.ElevatedButton(
        text="加载中...", 
        width=300, 
        height=50,
        on_click=lambda e: handle_auth_action(e)
    )

    # --- 核心逻辑 ---

    def on_profile_change(e):
        selected_name = profile_dropdown.value
        if not selected_name:
            return

        profile = pm.get_profile_by_name(selected_name)
        if not profile:
            return
        
        # [FIX 3] 这里赋值不再报错，因为类型是 Any
        current_profile_ref["value"] = profile
        
        # 切换数据库
        db.connect(profile.db_filename)
        
        config = db.get_config()
        is_reg = config.kdf_salt is None
        is_register_mode_ref["value"] = is_reg
        
        if is_reg:
            title_text.value = "初始化PasswordManger"
            sub_text.value = f"档案 '{profile.name}' 尚未设置主密码。"
            action_button.text = "设置密码并进入"
            pass_field.label = "设置新主密码"
        else:
            title_text.value = "解锁PasswordManger"
            sub_text.value = f"请输入 '{profile.name}' 的主密码。"
            action_button.text = "解锁"
            pass_field.label = "主密码"
            
        error_text.value = ""
        pass_field.value = ""
        
        if title_text.page:
            title_text.update()
            sub_text.update()
            action_button.update()
            pass_field.update()
            error_text.update()
            page.update()

    profile_dropdown.on_change = on_profile_change

    def refresh_profiles_list(select_last=False):
        pm.load_profiles()
        
        # [FIX 1 & 2] 确保 options 不为 None，满足类型检查
        if profile_dropdown.options is None:
            profile_dropdown.options = []
            
        profile_dropdown.options.clear()
        
        for p in pm.profiles:
            profile_dropdown.options.append(ft.dropdown.Option(text=p.name, key=p.name))
        
        if select_last and pm.profiles:
            profile_dropdown.value = pm.profiles[-1].name
        elif pm.profiles:
            # 尝试保持当前选中状态
            if profile_dropdown.value and pm.get_profile_by_name(profile_dropdown.value):
                pass 
            else:
                profile_dropdown.value = pm.profiles[0].name
            
        on_profile_change(None)
        
        if profile_dropdown.page:
            profile_dropdown.update()

    def handle_auth_action(e):
        password = pass_field.value
        if not password:
            error_text.value = "密码不能为空"
            error_text.update()
            return
        
        error_text.value = ""
        error_text.update()
        
        is_reg = is_register_mode_ref["value"]
        config = db.get_config()

        try:
            # 获取当前的 Profile 对象 (类型为 Profile 或 None)
            curr_profile: Optional[Profile] = current_profile_ref["value"]
            if not curr_profile:
                 error_text.value = "未选择档案"
                 error_text.update()
                 return

            if is_reg:
                salt = state.crypto.generate_salt()
                state.crypto.derive_key(password, salt)
                val_token = state.crypto.encrypt_text("VERIFY")
                
                db.update_config(kdf_salt=salt, validation_token=val_token)
                
                # [FIX 4] 使用中间变量 curr_profile 访问属性，不再报错
                print(f"Profile '{curr_profile.name}' 初始化成功。")
            else:
                current_salt = config.kdf_salt
                if not current_salt:
                    error_text.value = "数据库损坏：缺少 Salt"
                    error_text.update()
                    return
                
                state.crypto.derive_key(password, current_salt)
                
                if config.validation_token:
                    try:
                        check_str = state.crypto.decrypt_text(config.validation_token)
                        if check_str != "VERIFY":
                            raise InvalidToken
                    except InvalidToken:
                        state.clear()
                        error_text.value = "密码错误，请重试"
                        error_text.update()
                        return
                else:
                    pass 

            state.current_profile = curr_profile
            page.go("/vault")

        except Exception as ex:
            error_text.value = f"错误: {str(ex)}"
            error_text.update()

    # --- 新建档案弹窗 ---
    def show_add_profile_dialog(e):
        name_tf = ft.TextField(label="档案名称 (如: 公司账户)")
        server_tf = ft.TextField(label="服务器地址 (可选)")
        user_tf = ft.TextField(label="用户名 (可选)")
        
        def create_profile(e):
            name = name_tf.value or ""
            if not name: return
            
            if pm.get_profile_by_name(name):
                page.open(ft.SnackBar(ft.Text("档案名称已存在")))
                return
            
            pm.add_profile(
                name=name,
                server_url=server_tf.value or None,
                username=user_tf.value or None
            )
            page.close(dlg)
            refresh_profiles_list(select_last=True)
            page.open(ft.SnackBar(ft.Text(f"档案 {name} 创建成功")))

        dlg = ft.AlertDialog(
            title=ft.Text("新建账户档案"),
            content=ft.Column([
                name_tf,
                ft.Text("如果您想离线使用，下方留空即可。", size=12, color="grey"),
                server_tf,
                user_tf
            ], tight=True, width=350),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(dlg)),
                ft.ElevatedButton("创建", on_click=create_profile),
            ],
        )
        page.open(dlg)

    # --- 删除档案逻辑 ---
    def show_delete_confirm_dialog(e):
        current_name = profile_dropdown.value
        if not current_name: return

        def confirm_delete(e):
            pm.delete_profile(current_name)
            page.close(confirm_dlg)
            page.open(ft.SnackBar(ft.Text(f"档案 '{current_name}' 及其数据已彻底删除")))
            refresh_profiles_list()

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text(f"确定要删除档案 '{current_name}' 吗？\n\n该操作将永久删除本地所有密码数据，且不可恢复！", color="red"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: page.close(confirm_dlg)),
                ft.ElevatedButton("确认删除", color="white", bgcolor="red", on_click=confirm_delete),
            ],
        )
        page.open(confirm_dlg)

    # --- 初始化视图 ---
    refresh_profiles_list()

    return ft.View(
        "/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(name="security", size=80, color="blue"),
                        ft.Container(height=20),
                        
                        title_text,
                        sub_text,
                        ft.Container(height=30),
                        
                        ft.Row([
                            profile_dropdown,
                            ft.IconButton(
                                icon="add_circle", 
                                tooltip="新建档案", 
                                icon_color="blue",
                                on_click=show_add_profile_dialog
                            ),
                            ft.IconButton(
                                icon="delete_forever", 
                                tooltip="删除当前档案及数据", 
                                icon_color="red",
                                on_click=show_delete_confirm_dialog
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        
                        ft.Container(height=10),
                        pass_field,
                        error_text,
                        ft.Container(height=20),
                        action_button
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True
            )
        ]
    )