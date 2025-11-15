# sandbox/client/views/register.py
import flet as ft
import requests
from typing import Optional, cast
from src.client.database import db
from src.client.state import state 
from src.client.profile_manager import Profile, pm

def RegisterView(page: ft.Page):
    current_profile = cast(Optional[Profile], state.current_profile)
    current_url = "http://127.0.0.1:8000"
    if current_profile and current_profile.server_url:
        current_url = current_profile.server_url

    # 获取本地配置 
    config = db.get_config()
    
    # UI
    server_url_tf = ft.TextField(label="服务器地址", value=current_url)
    username_tf = ft.TextField(label="用户名")
    password_tf = ft.TextField(label="密码", password=True, can_reveal_password=True)
    confirm_pass_tf = ft.TextField(label="确认密码", password=True, can_reveal_password=True)
    
    status_text = ft.Text("", color="red")

    def handle_register(e):
        server_url = server_url_tf.value or ""
        user = username_tf.value or ""
        pwd = password_tf.value or ""
        confirm = confirm_pass_tf.value or ""

        if not server_url:
            status_text.value = "服务器地址不能为空"
            status_text.update()
            return

        if not user or not pwd:
            status_text.value = "用户名和密码不能为空"
            status_text.update()
            return
        
        if pwd != confirm:
            status_text.value = "两次输入的密码不一致"
            status_text.update()
            return

        if not config.kdf_salt:
            status_text.value = "错误：本地PasswordManger未初始化 (Salt缺失)。"
            status_text.update()
            return

        try:
            api_url = f"{server_url.rstrip('/')}/auth/register"
            
            resp = requests.post(api_url, json={
                "username": user,
                "password": pwd,
                "kdf_salt": config.kdf_salt
            }, timeout=5)

            if resp.status_code == 200:
                page.open(ft.SnackBar(ft.Text("注册成功！请返回登录")))
                
                # 如果当前有 Profile，更新
                if current_profile:
                    # 更新内存对象
                    current_profile.server_url = server_url
                    # 更新文件
                    pm.update_profile(current_profile.name, server_url=server_url)
                
                page.go("/vault")
            else:
                try:
                    err_msg = resp.json().get("detail", resp.text)
                except:
                    err_msg = resp.text
                status_text.value = f"注册失败: {err_msg}"
                status_text.update()
                
        except Exception as ex:
            status_text.value = f"连接错误: {ex}"
            status_text.update()

    return ft.View(
        "/register",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(name="person_add", size=80, color="green"),
                        ft.Text("注册同步账号", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("注册后可实现多端数据同步", size=14, color="grey"),
                        ft.Container(height=20),
                        
                        server_url_tf,
                        username_tf,
                        password_tf,
                        confirm_pass_tf,
                        
                        ft.Container(height=10),
                        status_text,
                        
                        ft.Container(height=20),
                        ft.ElevatedButton("立即注册", on_click=handle_register, width=300, height=45),
                        ft.TextButton("返回", on_click=lambda e: page.go("/vault"))
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=30
            )
        ]
    )