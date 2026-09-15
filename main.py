import flet as ft
from src.storage import VaultStorage
from src.ui.dashboard import Dashboard
import os
import threading

COLORS = getattr(ft, "Colors", None) or getattr(ft, "colors")


def run_flet(target, **kwargs):
    if hasattr(ft, "run"):
        return ft.run(target, **kwargs)
    return ft.app(target=target, **kwargs)


def flet_button(content, **kwargs):
    if hasattr(ft, "Button"):
        return ft.Button(content=content, **kwargs)
    return ft.ElevatedButton(content, **kwargs)


def show_snack(page, message, bgcolor=None):
    snack_bar = ft.SnackBar(ft.Text(message), bgcolor=bgcolor)
    if hasattr(page, "show_snack_bar"):
        page.show_snack_bar(snack_bar)
    elif hasattr(page, "open"):
        page.open(snack_bar)
    elif hasattr(page, "show_dialog"):
        page.show_dialog(snack_bar)
    else:
        page.snack_bar = snack_bar
        snack_bar.open = True
        page.update()


def is_android_page(page: ft.Page) -> bool:
    return "android" in str(getattr(page, "platform", "")).lower()


def main(page: ft.Page):
    page.title = "PassGuard Prototype"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0
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
            expand=True,
            on_submit=lambda e: unlock_clicked(e)
        )
        
        def unlock_clicked(e):
            try:
                # If it's a new file, load() returns an empty Vault
                vault = storage.load(password_input.value)
                current_password[0] = password_input.value
                show_dashboard(vault)
            except ValueError as ve:
                show_snack(page, str(ve), bgcolor=COLORS.ERROR)
                password_input.value = ""
            except Exception as ex:
                import traceback
                page.controls.clear()
                page.add(ft.Text(f"CRASH: {ex}\n\n{traceback.format_exc()}", color=COLORS.ERROR, selectable=True))
                page.update()

        page.add(ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=20,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=360,
                    content=ft.Column(
                        [
                            ft.Text("PassGuard Prototype", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text("Offline encrypted vault", color=COLORS.OUTLINE),
                            ft.Container(height=8),
                            password_input,
                            flet_button(
                                "Unlock",
                                icon=getattr(ft.Icons, "LOCK_OPEN", None),
                                on_click=unlock_clicked,
                                height=48,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        spacing=12,
                    ),
                ),
            ),
        ))
        password_input.focus()

    def show_dashboard(vault):
        active_vault = [vault]
        page.controls.clear()
        # Reset alignment for dashboard
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        
        def on_save(updated_vault):
            active_vault[0] = updated_vault
            if current_password[0]:
                storage.save(updated_vault, current_password[0])
                
        def on_lock():
            current_password[0] = None
            show_login()
            page.update()

        def on_change_password(current_password_attempt, new_password, updated_vault):
            if current_password_attempt != current_password[0]:
                raise ValueError("Current password is incorrect.")
            if active_vault[0]:
                storage.change_password(updated_vault, current_password[0], new_password)
                active_vault[0] = updated_vault
                current_password[0] = new_password

        def on_import_vault(import_path, import_password):
            if not current_password[0]:
                raise ValueError("Current vault session is locked.")
            imported_vault = storage.import_vault(import_path, import_password, current_password[0])
            active_vault[0] = imported_vault
            return imported_vault

        def on_import_vault_payload(import_payload, import_password):
            if not current_password[0]:
                raise ValueError("Current vault session is locked.")
            imported_vault = storage.import_vault_payload(import_payload, import_password, current_password[0])
            active_vault[0] = imported_vault
            return imported_vault

        def on_verify_backups():
            if not current_password[0]:
                raise ValueError("Current vault session is locked.")
            return storage.verify_backups(current_password[0])

        def on_shutdown():
            current_password[0] = None
            if is_android_page(page):
                show_login()
                page.update()
                return

            page.controls.clear()
            page.add(ft.Text("PassGuard Prototype has shut down.", color=COLORS.PRIMARY))
            page.update()

            window = getattr(page, "window", None)
            if window:
                close_window = getattr(window, "destroy", None) or getattr(window, "close", None)
                if close_window:
                    close_window()
                    return

            threading.Timer(0.2, lambda: os._exit(0)).start()

        dashboard = Dashboard(vault, storage.filepath, on_save, on_lock, on_change_password, on_import_vault, on_import_vault_payload, on_verify_backups, on_shutdown)
        page.add(dashboard)

    show_login()

if __name__ == "__main__":
    run_flet(main)
