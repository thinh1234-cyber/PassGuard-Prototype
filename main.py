import flet as ft
from src.storage import VaultStorage
from src.ui.dashboard import Dashboard

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
                traceback.print_exc()
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ft.colors.ERROR)
                page.snack_bar.open = True
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
        
        def on_save(updated_vault):
            if current_password[0]:
                storage.save(updated_vault, current_password[0])
                
        def on_lock():
            current_password[0] = None
            show_login()

        dashboard = Dashboard(vault, on_save, on_lock)
        page.add(dashboard)

    show_login()

if __name__ == "__main__":
    ft.app(target=main)
