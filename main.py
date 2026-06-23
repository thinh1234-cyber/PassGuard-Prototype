import flet as ft
from src.storage import VaultStorage

def main(page: ft.Page):
    page.title = "LuuPass"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    storage = VaultStorage()

    def unlock_clicked(e):
        try:
            vault = storage.load(password_input.value)
            page.snack_bar = ft.SnackBar(ft.Text(f"Unlocked! Entries: {len(vault.entries)}"))
            page.snack_bar.open = True
            page.update()
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text("Wrong Password!"), bgcolor=ft.colors.ERROR)
            page.snack_bar.open = True
            page.update()

    password_input = ft.TextField(label="Master Password", password=True, can_reveal_password=True, width=300)
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

if __name__ == "__main__":
    ft.app(target=main)
