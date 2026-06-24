import flet as ft
from src.storage import VaultStorage
from src.ui.dashboard import Dashboard
import secrets
import sys

SESSION_TOKEN = secrets.token_urlsafe(16)
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
    if hasattr(page, "show_dialog"):
        page.show_dialog(snack_bar)
    elif hasattr(page, "open"):
        page.open(snack_bar)
    else:
        page.snack_bar = snack_bar
        snack_bar.open = True
        page.update()

def main(page: ft.Page):
    if "--web" in sys.argv:
        if page.route != f"/{SESSION_TOKEN}":
            page.title = "Access Denied"
            page.controls.clear()
            page.add(ft.Text("403 Forbidden: Invalid or missing token. Please use the terminal link.", color=COLORS.ERROR, size=20))
            page.update()
            return

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
            except ValueError as ve:
                show_snack(page, str(ve), bgcolor=COLORS.ERROR)
                password_input.value = ""
            except Exception as ex:
                import traceback
                page.controls.clear()
                page.add(ft.Text(f"CRASH: {ex}\n\n{traceback.format_exc()}", color=COLORS.ERROR, selectable=True))
                page.update()

        page.add(
            ft.Column(
                [
                    ft.Text("LuuPass Vault", size=30, weight=ft.FontWeight.BOLD), 
                    password_input, 
                    flet_button("Unlock", on_click=unlock_clicked)
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
            page.update()

        def on_change_password(new_password):
            current_password[0] = new_password
            if vault:
                storage.save(vault, current_password[0], keep_backups=False)

        def on_import_vault(import_path, import_password):
            return storage.import_vault(import_path, import_password)

        dashboard = Dashboard(vault, storage.filepath, on_save, on_lock, on_change_password, on_import_vault)
        page.add(dashboard)

    show_login()

if __name__ == "__main__":
    if "--web" in sys.argv:
        import threading
        import webbrowser
        import time
        
        # Monkey-patch to block Flet from opening the unauthenticated root URL
        original_open = webbrowser.open
        webbrowser.open = lambda url, new=0, autoraise=True: None
        
        url = f"http://127.0.0.1:8550/{SESSION_TOKEN}"
        print("="*60)
        print("="*60)
        print("LuuPass Vault is running securely in Local Web Mode!")
        print(f"Please open this link to access your vault:\n\n   {url}\n")
        print("="*60)
        
        def open_browser():
            time.sleep(1.5)
            import subprocess
            import os
            
            is_termux = "com.termux" in os.environ.get("PREFIX", "")
            opened = False
            
            if is_termux:
                try:
                    # Android Termux: Try Chrome Incognito
                    subprocess.run([
                        "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main", 
                        "-d", url, "--es", "com.google.android.apps.chrome.EXTRA_OPEN_NEW_INCOGNITO_TAB", "true"
                    ], check=True, capture_output=True)
                    opened = True
                except Exception:
                    pass
            elif sys.platform == "win32":
                try:
                    # Windows: Try Chrome Incognito
                    subprocess.run(["cmd", "/c", f"start chrome --incognito {url}"], check=True, capture_output=True)
                    opened = True
                except Exception:
                    pass
            
            if not opened:
                # Fallback to default browser
                original_open(url)
            
        threading.Thread(target=open_browser, daemon=True).start()
        
        run_flet(main, view=ft.AppView.WEB_BROWSER, port=8550, host="127.0.0.1")
    else:
        run_flet(main)
