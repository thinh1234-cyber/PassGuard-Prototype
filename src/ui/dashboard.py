import flet as ft
from src.models import Vault, Entry, Account
import shutil
import os
import hashlib
import platform
import threading


COLORS = getattr(ft, "Colors", None) or getattr(ft, "colors")
ICONS = getattr(ft, "Icons", None) or getattr(ft, "icons")


def flet_button(content, **kwargs):
    if hasattr(ft, "Button"):
        return ft.Button(content=content, **kwargs)
    return ft.ElevatedButton(content, **kwargs)


class Dashboard(ft.Container):
    def __init__(self, vault: Vault, vault_filepath, on_save, on_lock, on_change_password, on_import_vault):
        super().__init__(expand=True)
        self.vault = vault
        self.vault_filepath = vault_filepath
        self.on_save = on_save
        self.on_lock = on_lock
        self.on_change_password = on_change_password
        self.on_import_vault = on_import_vault
        self.selected_entry = None
        self.show_settings = False
        self.search_query = ""
        self.pending_import_path = None
        self.clipboard_clear_timer = None
        self.entries_list_view = ft.ListView(expand=True, spacing=10, padding=20)
        self.detail_view_container = ft.Container(expand=True, padding=20, bgcolor=COLORS.SURFACE_VARIANT, border_radius=10)
        
        self.export_picker = ft.FilePicker(on_result=self.export_result)
        self.import_picker = ft.FilePicker(on_result=self.import_result)
        
        self._build_ui()

    def show_snack(self, message, bgcolor=None):
        snack_bar = ft.SnackBar(ft.Text(message), bgcolor=bgcolor)
        if hasattr(self.page, "show_dialog"):
            self.page.show_dialog(snack_bar)
        elif hasattr(self.page, "open"):
            self.page.open(snack_bar)
        else:
            self.page.snack_bar = snack_bar
            snack_bar.open = True
            self.page.update()

    def show_dialog(self, dialog):
        if hasattr(self.page, "show_dialog"):
            self.page.show_dialog(dialog)
        elif hasattr(self.page, "open"):
            self.page.open(dialog)
        else:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def close_dialog(self, dialog):
        if hasattr(self.page, "pop_dialog"):
            self.page.pop_dialog()
        elif hasattr(self.page, "close"):
            self.page.close(dialog)
        else:
            dialog.open = False
            self.page.update()

    def did_mount(self):
        self.page.overlay.extend([self.export_picker, self.import_picker])
        self.page.on_resize = self.handle_resize
        self.handle_resize()
        self.page.update()

    def handle_resize(self, e=None):
        if not self.page:
            return
        is_mobile = self.page.width < 800

        if is_mobile:
            self.top_bar.visible = True
            self.list_container.expand = True
            self.detail_view_container.expand = True
            
            if self.selected_entry or self.show_settings:
                self.btn_back.visible = True
                self.content = ft.Column([
                    self.top_bar,
                    self.detail_view_container
                ], expand=True)
            else:
                self.btn_back.visible = False
                self.content = ft.Column([
                    self.top_bar,
                    self.list_container
                ], expand=True)
        else:
            self.top_bar.visible = False
            self.list_container.expand = False
            self.list_container.width = 300
            self.detail_view_container.expand = True
            
            self.content = ft.Column([
                ft.Row([
                    self.sidebar,
                    ft.VerticalDivider(width=1),
                    self.list_container,
                    ft.VerticalDivider(width=1),
                    self.detail_view_container
                ], expand=True)
            ], expand=True)

        self.update()

    def _build_ui(self):
        self.btn_back = ft.IconButton(ICONS.ARROW_BACK, on_click=self.go_back, visible=False)
        self.top_bar = ft.Container(
            content=ft.Row([
                self.btn_back,
                ft.Text("LuuPass", size=20, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(ICONS.ADD, on_click=self.add_new_entry, tooltip="Add Platform"),
                ft.IconButton(ICONS.SETTINGS, on_click=self.open_settings, tooltip="Settings"),
                ft.IconButton(ICONS.LOCK, on_click=lambda e: self.on_lock(), tooltip="Lock Vault")
            ]),
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            bgcolor=COLORS.SURFACE,
            visible=False
        )

        self.sidebar = ft.Container(
            content=ft.Column([
                ft.Text("LuuPass", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.TextButton("All Items", icon=ICONS.LIST, on_click=lambda e: self.select_entry(None)),
                ft.TextButton("Add New Platform", icon=ICONS.ADD, on_click=self.add_new_entry),
                ft.Container(expand=True),  # Pushes the below items to the bottom
                ft.Divider(),
                ft.TextButton("Settings", icon=ICONS.SETTINGS, on_click=self.open_settings),
                ft.TextButton("Lock Vault", icon=ICONS.LOCK, on_click=lambda e: self.on_lock())
            ]),
            width=200,
            padding=20,
            bgcolor=COLORS.SURFACE
        )

        self.search_field = ft.TextField(
            hint_text="Search...", 
            prefix_icon=ICONS.SEARCH, 
            on_change=self.on_search_change,
            border_radius=20,
            content_padding=10
        )
        self.list_container = ft.Container(
            content=ft.Column([
                ft.Container(self.search_field, padding=10),
                ft.Container(self.entries_list_view, expand=True)
            ]), 
            width=300
        )
        
        self.content = ft.Column([], expand=True) # Will be populated by handle_resize

        self.update_list_view()
        self.update_detail_view()

    def on_search_change(self, e):
        
        self.search_query = e.control.value
        self.update_list_view()

    def get_offline_favicon(self, title):
        letter = title[0].upper() if title else "?"
        colors = [
            COLORS.RED, COLORS.BLUE, COLORS.GREEN, COLORS.ORANGE, 
            COLORS.PURPLE, COLORS.TEAL, COLORS.PINK, COLORS.BROWN
        ]
        color_idx = int(hashlib.md5((title or "").encode('utf-8')).hexdigest(), 16) % len(colors)
        return ft.CircleAvatar(content=ft.Text(letter, color=COLORS.WHITE), bgcolor=colors[color_idx])

    def update_list_view(self):
        self.entries_list_view.controls.clear()
        query = self.search_query.lower()
        
        for entry in self.vault.entries:
            if query:
                match = False
                if query in (entry.title or "").lower() or query in (entry.url or "").lower():
                    match = True
                else:
                    for acc in entry.accounts:
                        if query in (acc.username or "").lower():
                            match = True
                            break
                if not match:
                    continue

            leading_icon = self.get_offline_favicon(entry.title)

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
        if getattr(self.entries_list_view, "page", None):
            self.entries_list_view.update()

    def select_entry(self, entry):
        
        self.show_settings = False
        self.selected_entry = entry
        self.update_list_view()
        self.update_detail_view()
        self.handle_resize()

    def open_settings(self, e):
        
        self.show_settings = True
        self.selected_entry = None
        self.update_list_view()
        self.update_detail_view()
        self.handle_resize()

    def go_back(self, e):
        
        self.show_settings = False
        self.selected_entry = None
        self.update_list_view()
        self.update_detail_view()
        self.handle_resize()

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
        self.handle_resize()

    def save_current_entry(self, e):
        
        self.on_save(self.vault)
        self.update_list_view()
        if self.page:
            self.show_snack("Platform Saved Successfully!", bgcolor=COLORS.GREEN)

    def export_result(self, e):
        
        if e.path:
            try:
                shutil.copy(self.vault_filepath, e.path)
                self.show_snack("Vault Exported Successfully!", bgcolor=COLORS.GREEN)
            except Exception as ex:
                self.show_snack(f"Export Error: {ex}", bgcolor=COLORS.ERROR)

    def import_result(self, e):
        
        if e.files and len(e.files) > 0:
            self.pending_import_path = e.files[0].path
            self.open_import_password_dialog()

    def open_import_password_dialog(self):
        password_field = ft.TextField(
            label="Import Vault Password",
            password=True,
            can_reveal_password=True,
            width=320,
        )

        def close_dialog(e=None):
            self.pending_import_path = None
            self.close_dialog(dialog)

        def confirm_import(e=None):
            if not password_field.value:
                self.show_snack("Please enter the import vault password.", bgcolor=COLORS.ERROR)
                return

            try:
                self.on_import_vault(self.pending_import_path, password_field.value)
                password_field.value = ""
                self.pending_import_path = None
                self.close_dialog(dialog)
                self.show_snack(
                    "Vault imported successfully. Unlock again with the imported vault password.",
                    bgcolor=COLORS.GREEN,
                )
                self.on_lock()
            except Exception as ex:
                password_field.value = ""
                self.show_snack(f"Import Error: {ex}", bgcolor=COLORS.ERROR)

        password_field.on_submit = confirm_import
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Validate Import Vault"),
            content=ft.Column(
                [
                    ft.Text("Enter the master password for the selected vault before replacing the current vault."),
                    password_field,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                flet_button("Import", icon=ICONS.UPLOAD, on_click=confirm_import),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.show_dialog(dialog)
        password_field.focus()

    def toggle_theme(self, e):
        
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
        self.page.update()

    def build_settings_view(self):
        theme_btn = flet_button("Toggle Light/Dark Mode", icon=ICONS.PALETTE, on_click=self.toggle_theme)
        
        default_export = "/storage/emulated/0/Download" if "android" in platform.platform().lower() else os.path.expanduser("~/Downloads")
        export_path_field = ft.TextField(label="Export Folder Path", value=default_export, expand=True)
        
        def export_to_path(e):
            
            dest_dir = export_path_field.value
            if not os.path.exists(dest_dir):
                self.show_snack(f"Directory not found: {dest_dir}", bgcolor=COLORS.ERROR)
            else:
                dest_file = os.path.join(dest_dir, "vault_backup.luupass")
                try:
                    shutil.copy(self.vault_filepath, dest_file)
                    self.show_snack(f"Exported to {dest_file}!", bgcolor=COLORS.GREEN)
                except Exception as ex:
                    self.show_snack(f"Export Error: {ex}", bgcolor=COLORS.ERROR)

        export_btn = flet_button("Export to Folder", icon=ICONS.DOWNLOAD, on_click=export_to_path)
        
        import_btn = flet_button(
            "Import Vault (.luupass)", 
            icon=ICONS.UPLOAD, 
            on_click=lambda _: self.import_picker.pick_files(allowed_extensions=["luupass"])
        )

        new_pass_field = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300)
        
        def change_pass_clicked(e):
            
            if new_pass_field.value:
                self.on_change_password(new_pass_field.value)
                new_pass_field.value = ""
                if getattr(new_pass_field, "page", None):
                    new_pass_field.update()
                self.show_snack("Password Changed Successfully!", bgcolor=COLORS.GREEN)

        change_pass_btn = flet_button("Change Password", icon=ICONS.PASSWORD, on_click=change_pass_clicked)

        return ft.Column([
            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("UI Configuration", weight=ft.FontWeight.BOLD, size=20),
            theme_btn,
            ft.Container(height=20),
            ft.Text("Change Master Password", weight=ft.FontWeight.BOLD, size=20),
            ft.Row([new_pass_field, change_pass_btn]),
            ft.Container(height=20),
            ft.Text("Data Management", weight=ft.FontWeight.BOLD, size=20),
            ft.Text("Warning: Importing will replace your current local vault. Make sure to export a backup first!", color=COLORS.ERROR),
            ft.Row([export_path_field, export_btn]),
            ft.Container(height=10),
            ft.Row([import_btn]),
        ], scroll=ft.ScrollMode.AUTO)

    def update_detail_view(self):
        if self.show_settings:
            self.detail_view_container.content = self.build_settings_view()
        elif not self.selected_entry:
            self.detail_view_container.content = ft.Container(
                content=ft.Text("Select a platform to view details", color=COLORS.ON_SURFACE_VARIANT),
                alignment=ft.Alignment.CENTER
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
                self.show_snack("Copied to clipboard! (Auto-clears in 15s)")

                if self.clipboard_clear_timer:
                    self.clipboard_clear_timer.cancel()
                
                def clear_clipboard():
                    if self.page and self.clipboard_clear_timer is t:
                        self.page.set_clipboard("")
                        self.clipboard_clear_timer = None
                
                t = threading.Timer(15.0, clear_clipboard)
                t.daemon = True
                self.clipboard_clear_timer = t
                t.start()

            accounts_col = ft.Column(spacing=10)
            
            def build_account_row(account):
                row_container = ft.Container(padding=10, border=ft.Border.all(1, COLORS.OUTLINE), border_radius=5)
                
                def update_acc(field, value):
                    setattr(account, field, value)
                
                u_field = ft.TextField(label="Username", value=account.username, on_change=lambda e: update_acc('username', e.control.value), expand=True)
                p_field = ft.TextField(label="Password", value=account.password, password=True, can_reveal_password=True, on_change=lambda e: update_acc('password', e.control.value), expand=True)
                
                def remove_acc(e):
                    for i, a in enumerate(entry.accounts):
                        if a is account:
                            entry.accounts.pop(i)
                            break
                    if row_container in accounts_col.controls:
                        accounts_col.controls.remove(row_container)
                    if getattr(accounts_col, "page", None):
                        accounts_col.update()
                    if self.page:
                        self.page.update()
                
                row_container.content = ft.Column([
                    ft.Row([
                        u_field, 
                        ft.IconButton(icon=ICONS.COPY, on_click=lambda e: copy_to_clipboard(u_field.value))
                    ]),
                    ft.Row([
                        p_field, 
                        ft.IconButton(icon=ICONS.COPY, on_click=lambda e: copy_to_clipboard(p_field.value)),
                        ft.IconButton(icon=ICONS.REMOVE_CIRCLE, icon_color=COLORS.ERROR, tooltip="Remove Account", on_click=remove_acc)
                    ])
                ])
                return row_container

            for acc in entry.accounts:
                accounts_col.controls.append(build_account_row(acc))

            def add_account(e):
                new_acc = Account(username="", password="")
                entry.accounts.append(new_acc)
                accounts_col.controls.append(build_account_row(new_acc))
                if getattr(accounts_col, "page", None):
                    accounts_col.update()
                if self.page:
                    self.page.update()

            actions_row = ft.Row([
                flet_button("Add Another Account", icon=ICONS.ADD, on_click=add_account),
                ft.Container(expand=True),
                ft.IconButton(icon=ICONS.DELETE, icon_color=COLORS.ERROR, tooltip="Delete Entire Platform", on_click=lambda e: self.delete_entry(entry)),
                flet_button("Save Changes", icon=ICONS.SAVE, bgcolor=COLORS.PRIMARY, color=COLORS.ON_PRIMARY, on_click=self.save_current_entry)
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

        if getattr(self.detail_view_container, "page", None):
            self.detail_view_container.update()
