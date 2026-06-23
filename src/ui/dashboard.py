import flet as ft
from src.models import Vault, Entry, Account
import urllib.parse
import shutil
import os

class Dashboard(ft.Container):
    def __init__(self, vault: Vault, on_save, on_lock, on_reload):
        super().__init__(expand=True)
        self.vault = vault
        self.on_save = on_save
        self.on_lock = on_lock
        self.on_reload = on_reload
        self.selected_entry = None
        self.show_settings = False
        self.entries_list_view = ft.ListView(expand=1, spacing=10, padding=20)
        self.detail_view_container = ft.Container(expand=2, padding=20, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=10)
        
        self.export_picker = ft.FilePicker(on_result=self.export_result)
        self.import_picker = ft.FilePicker(on_result=self.import_result)
        
        self._build_ui()

    def did_mount(self):
        self.page.overlay.extend([self.export_picker, self.import_picker])
        self.page.update()

    def _build_ui(self):
        self.update_list_view()
        self.update_detail_view()

        sidebar = ft.Container(
            content=ft.Column([
                ft.Text("LuuPass", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.TextButton("All Items", icon=ft.icons.LIST, on_click=lambda e: self.select_entry(None)),
                ft.TextButton("Add New Platform", icon=ft.icons.ADD, on_click=self.add_new_entry),
                ft.Container(expand=True),  # Pushes the below items to the bottom
                ft.Divider(),
                ft.TextButton("Settings", icon=ft.icons.SETTINGS, on_click=self.open_settings),
                ft.TextButton("Lock Vault", icon=ft.icons.LOCK, on_click=lambda e: self.on_lock())
            ]),
            width=200,
            padding=20,
            bgcolor=ft.colors.SURFACE
        )

        self.content = ft.Row([
            sidebar,
            ft.VerticalDivider(width=1),
            ft.Container(content=self.entries_list_view, width=300),
            ft.VerticalDivider(width=1),
            self.detail_view_container
        ], expand=True)

    def get_favicon_url(self, url):
        if not url:
            return None
        if not url.startswith("http"):
            url = "https://" + url
        try:
            domain = urllib.parse.urlparse(url).netloc
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
        except Exception:
            return None

    def update_list_view(self):
        self.entries_list_view.controls.clear()
        for entry in self.vault.entries:
            favicon = self.get_favicon_url(entry.url)
            if favicon:
                leading_icon = ft.Image(src=favicon, width=24, height=24, border_radius=12)
            else:
                leading_icon = ft.Icon(ft.icons.LANGUAGE)

            acc_count = len(entry.accounts)
            subtitle = f"{acc_count} account{'s' if acc_count != 1 else ''}"
            
            self.entries_list_view.controls.append(
                ft.ListTile(
                    title=ft.Text(entry.title if entry.title else "Untitled"),
                    subtitle=ft.Text(subtitle),
                    leading=leading_icon,
                    on_click=lambda e, entry=entry: self.select_entry(entry),
                    selected=(self.selected_entry == entry and not self.show_settings)
                )
            )
        if self.page:
            self.entries_list_view.update()

    def select_entry(self, entry):
        self.show_settings = False
        self.selected_entry = entry
        self.update_list_view()
        self.update_detail_view()

    def open_settings(self, e):
        self.show_settings = True
        self.selected_entry = None
        self.update_list_view()
        self.update_detail_view()

    def add_new_entry(self, e):
        self.show_settings = False
        new_entry = Entry(title="New Platform", accounts=[Account(username="", password="")])
        self.vault.entries.append(new_entry)
        self.select_entry(new_entry)

    def delete_entry(self, entry):
        self.vault.entries.remove(entry)
        self.selected_entry = None
        self.on_save(self.vault)
        self.update_list_view()
        self.update_detail_view()

    def save_current_entry(self, e):
        self.on_save(self.vault)
        self.update_list_view()
        if self.page:
            self.page.snack_bar = ft.SnackBar(ft.Text("Platform Saved Successfully!"), bgcolor=ft.colors.GREEN)
            self.page.snack_bar.open = True
            self.page.update()

    def export_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                shutil.copy("vault.luupass", e.path)
                self.page.snack_bar = ft.SnackBar(ft.Text("Vault Exported Successfully!"), bgcolor=ft.colors.GREEN)
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Export Error: {ex}"), bgcolor=ft.colors.ERROR)
            self.page.snack_bar.open = True
            self.page.update()

    def import_result(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            try:
                shutil.copy(e.files[0].path, "vault.luupass")
                self.page.snack_bar = ft.SnackBar(ft.Text("Vault Imported Successfully! Please unlock again."), bgcolor=ft.colors.GREEN)
                self.page.snack_bar.open = True
                self.page.update()
                # Lock the vault so they re-authenticate with the new file
                self.on_lock()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Import Error: {ex}"), bgcolor=ft.colors.ERROR)
                self.page.snack_bar.open = True
                self.page.update()

    def toggle_theme(self, e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
        self.page.update()

    def build_settings_view(self):
        theme_btn = ft.ElevatedButton("Toggle Light/Dark Mode", icon=ft.icons.PALETTE, on_click=self.toggle_theme)
        
        export_btn = ft.ElevatedButton(
            "Export Vault (.luupass)", 
            icon=ft.icons.DOWNLOAD, 
            on_click=lambda _: self.export_picker.save_file(allowed_extensions=["luupass"])
        )
        
        import_btn = ft.ElevatedButton(
            "Import Vault (.luupass)", 
            icon=ft.icons.UPLOAD, 
            on_click=lambda _: self.import_picker.pick_files(allowed_extensions=["luupass"])
        )

        return ft.Column([
            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("UI Configuration", weight=ft.FontWeight.BOLD, size=20),
            theme_btn,
            ft.Container(height=20),
            ft.Text("Data Management", weight=ft.FontWeight.BOLD, size=20),
            ft.Text("Warning: Importing will replace your current local vault. Make sure to export a backup first!", color=ft.colors.ERROR),
            ft.Row([export_btn, import_btn]),
        ])

    def update_detail_view(self):
        if self.show_settings:
            self.detail_view_container.content = self.build_settings_view()
        elif not self.selected_entry:
            self.detail_view_container.content = ft.Container(
                content=ft.Text("Select a platform to view details", color=ft.colors.ON_SURFACE_VARIANT),
                alignment=ft.alignment.center
            )
        else:
            entry = self.selected_entry
            
            def update_entry_field(field, value):
                setattr(entry, field, value)

            title_field = ft.TextField(label="Platform / Title", value=entry.title, on_change=lambda e: update_entry_field('title', e.control.value), expand=True)
            url_field = ft.TextField(label="URL", value=entry.url, on_change=lambda e: update_entry_field('url', e.control.value), expand=True)
            notes_field = ft.TextField(label="Notes", value=entry.notes, multiline=True, on_change=lambda e: update_entry_field('notes', e.control.value))

            def copy_to_clipboard(val):
                self.page.set_clipboard(val)
                self.page.snack_bar = ft.SnackBar(ft.Text("Copied to clipboard!"))
                self.page.snack_bar.open = True
                self.page.update()

            accounts_col = ft.Column(spacing=10)
            
            def build_account_row(account):
                def update_acc(field, value):
                    setattr(account, field, value)
                
                u_field = ft.TextField(label="Username", value=account.username, on_change=lambda e: update_acc('username', e.control.value), expand=True)
                p_field = ft.TextField(label="Password", value=account.password, password=True, can_reveal_password=True, on_change=lambda e: update_acc('password', e.control.value), expand=True)
                
                def remove_acc(e):
                    entry.accounts.remove(account)
                    self.update_detail_view()
                
                return ft.Container(
                    content=ft.Column([
                        ft.Row([
                            u_field, 
                            ft.IconButton(icon=ft.icons.COPY, on_click=lambda e: copy_to_clipboard(u_field.value))
                        ]),
                        ft.Row([
                            p_field, 
                            ft.IconButton(icon=ft.icons.COPY, on_click=lambda e: copy_to_clipboard(p_field.value)),
                            ft.IconButton(icon=ft.icons.REMOVE_CIRCLE, icon_color=ft.colors.ERROR, tooltip="Remove Account", on_click=remove_acc)
                        ])
                    ]),
                    padding=10, border=ft.border.all(1, ft.colors.OUTLINE), border_radius=5
                )

            for acc in entry.accounts:
                accounts_col.controls.append(build_account_row(acc))

            def add_account(e):
                entry.accounts.append(Account())
                self.update_detail_view()

            actions_row = ft.Row([
                ft.ElevatedButton("Add Another Account", icon=ft.icons.ADD, on_click=add_account),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.icons.DELETE, icon_color=ft.colors.ERROR, tooltip="Delete Entire Platform", on_click=lambda e: self.delete_entry(entry)),
                ft.ElevatedButton("Save Changes", icon=ft.icons.SAVE, bgcolor=ft.colors.PRIMARY, color=ft.colors.ON_PRIMARY, on_click=self.save_current_entry)
            ])

            self.detail_view_container.content = ft.Column([
                ft.Row([title_field, url_field]),
                ft.Divider(),
                ft.Text("Accounts", weight=ft.FontWeight.BOLD),
                accounts_col,
                actions_row,
                ft.Divider(),
                notes_field,
            ], scroll=ft.ScrollMode.AUTO)

        if self.page:
            self.detail_view_container.update()
