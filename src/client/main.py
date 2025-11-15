import flet as ft
import traceback

try:
    from src.client.views.login import LoginView
    from src.client.views.vault import VaultView
    from src.client.views.register import RegisterView
    from src.client.views.sync_center import SyncCenterView
except ImportError as e:
    print(f"视图导入失败: {e}")
    traceback.print_exc()

def main(page: ft.Page):
    page.title = "Password Manager"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    def route_change(route):
        print(f"路由正在切换: {page.route}")
        page.window.icon = "icon.png"
        # 弹窗清理
        page.overlay.clear()
        
        page.views.clear()
        
        try:
            if page.route == "/login":
                page.views.append(LoginView(page))
            
            elif page.route == "/vault":
                page.views.append(VaultView(page))
            
            elif page.route == "/register":
                page.views.append(RegisterView(page))
            
            elif page.route == "/sync_center":
                page.views.append(SyncCenterView(page))
                
            page.update()
            print(f"视图更新完成. Views: {len(page.views)}")

        except Exception as e:
            print(f"CRITICAL ERROR in route_change: {e}")
            traceback.print_exc()

    def view_pop(view):
        print(f"触发 view_pop. 当前 Views 数量: {len(page.views)}")
        
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route or "/")
        else:
            print("出现错误，强制重建当前视图")
            route_change(page.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)