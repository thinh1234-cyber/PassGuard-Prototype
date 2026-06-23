import flet as ft
from src.storage import VaultStorage
from src.ui.dashboard import Dashboard
import threading

def main(page: ft.Page):
    page.title = "LuuPass"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    storage = VaultStorage()
    current_password = [None]  # To keep track of the session password

    def show_login():
        page.controls.clear()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        password_input = ft.TextField(
            label="Master Password", 
            password=True, 
            can_reveal_password=True, 
            width=300,
            on_submit=lambda e: unlock_clicked(e)
        )
        
        def unlock_clicked(e):
            try:
                # If it's a new file, load() returns an empty Vault
                vault = storage.load(password_input.value)
                current_password[0] = password_input.value
                show_dashboard(vault)
            except Exception as ex:
                import traceback
                page.controls.clear()
                page.add(ft.Text(f"CRASH: {ex}\n\n{traceback.format_exc()}", color=ft.colors.ERROR, selectable=True))
                page.update()

        page.add(
            ft.Column(
                [
                    ft.Text("LuuPass Vault", size=30, weight=ft.FontWeight.BOLD), 
                    password_input, 
                    ft.ElevatedButton("Unlock", on_click=unlock_clicked)
                ],
                alignment=ft.MainAxisAlignment.CENTER, 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )
        password_input.focus()

    def show_dashboard(vault):
        page.controls.clear()
        # Reset alignment for dashboard
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        
        def do_lock():
            current_password[0] = None
            show_login()
            page.update()

        class AutoLocker:
            def __init__(self):
                self.timer = None
            def reset(self):
                if self.timer:
                    self.timer.cancel()
                self.timer = threading.Timer(300, do_lock) # 5 minutes auto-lock
                self.timer.daemon = True
                self.timer.start()
            def cancel(self):
                if self.timer:
                    self.timer.cancel()

        auto_locker = AutoLocker()
        auto_locker.reset()
        
        def on_save(updated_vault):
            if current_password[0]:
                storage.save(updated_vault, current_password[0])
                
        def on_lock():
            auto_locker.cancel()
            do_lock()

        def on_change_password(new_password):
            current_password[0] = new_password
            if vault:
                storage.save(vault, current_password[0])

        dashboard = Dashboard(vault, on_save, on_lock, on_change_password, auto_locker.reset)
        page.add(dashboard)

    show_login()

if __name__ == "__main__":
    import sys
    if "--web" in sys.argv:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)
    else:
        ft.app(target=main)
