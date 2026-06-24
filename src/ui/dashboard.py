import hashlib
import inspect
import os
import platform
import shutil
import threading

import flet as ft

from src.models import Account, Entry, Vault


COLORS = getattr(ft, "Colors", None) or getattr(ft, "colors")
ICONS = getattr(ft, "Icons", None) or getattr(ft, "icons")

DARK_PALETTE = {
    "BG": "#12131b",
    "SHELL": "#151720",
    "SIDEBAR": "#0d0e16",
    "SURFACE": "#1a1b23",
    "SURFACE_LOW": "#1f1f27",
    "SURFACE_HIGH": "#292932",
    "SURFACE_HIGHEST": "#34343d",
    "TEXT": "#e3e1ed",
    "MUTED": "#c6c5d7",
    "OUTLINE": "#454655",
    "BORDER": "#242632",
    "PRIMARY": "#bec2ff",
    "PRIMARY_CONTAINER": "#5865f2",
    "ON_PRIMARY": "#000da4",
    "SUCCESS": "#4edea3",
    "ERROR": "#ffb4ab",
    "WARNING_BG": "#22191b",
    "WARNING_BORDER": "#4a2c31",
}

LIGHT_PALETTE = {
    "BG": "#f6f7fb",
    "SHELL": "#ffffff",
    "SIDEBAR": "#eef1f8",
    "SURFACE": "#ffffff",
    "SURFACE_LOW": "#f1f3f9",
    "SURFACE_HIGH": "#e7eaf4",
    "SURFACE_HIGHEST": "#dce1ef",
    "TEXT": "#171923",
    "MUTED": "#596174",
    "OUTLINE": "#ccd2e0",
    "BORDER": "#d9deea",
    "PRIMARY": "#3f4cda",
    "PRIMARY_CONTAINER": "#5865f2",
    "ON_PRIMARY": "#ffffff",
    "SUCCESS": "#00865c",
    "ERROR": "#b3261e",
    "WARNING_BG": "#fff3f1",
    "WARNING_BORDER": "#ffd7d2",
}

BG = SURFACE = SURFACE_LOW = SURFACE_HIGH = SURFACE_HIGHEST = TEXT = MUTED = OUTLINE = PRIMARY = PRIMARY_CONTAINER = ON_PRIMARY = SUCCESS = ERROR = "#000000"
SHELL = SIDEBAR = BORDER = WARNING_BG = WARNING_BORDER = "#000000"


def apply_palette(mode="dark"):
    palette = LIGHT_PALETTE if mode == "light" else DARK_PALETTE
    globals().update(palette)


apply_palette("dark")


def padding_symmetric(horizontal=0, vertical=0):
    return ft.Padding(horizontal, vertical, horizontal, vertical)


def padding_only(**kwargs):
    left = kwargs.get("left", 0)
    top = kwargs.get("top", 0)
    right = kwargs.get("right", 0)
    bottom = kwargs.get("bottom", 0)
    return ft.Padding(left, top, right, bottom)


def margin_only(**kwargs):
    left = kwargs.get("left", 0)
    top = kwargs.get("top", 0)
    right = kwargs.get("right", 0)
    bottom = kwargs.get("bottom", 0)
    return ft.Margin(left, top, right, bottom)


def border_all(width=1, color=OUTLINE):
    if hasattr(ft, "Border") and hasattr(ft, "BorderSide"):
        side = ft.BorderSide(width, color)
        return ft.Border(top=side, right=side, bottom=side, left=side)
    return ft.border.all(width, color)


def border_only(**kwargs):
    if hasattr(ft, "Border"):
        return ft.Border(
            top=kwargs.get("top"),
            right=kwargs.get("right"),
            bottom=kwargs.get("bottom"),
            left=kwargs.get("left"),
        )
    return ft.border.only(**kwargs)


def alignment_center():
    if hasattr(ft, "Alignment") and hasattr(ft.Alignment, "CENTER"):
        return ft.Alignment.CENTER
    return ft.alignment.center


def flet_button(content, **kwargs):
    if hasattr(ft, "Button"):
        return ft.Button(content=content, **kwargs)
    return ft.ElevatedButton(content, **kwargs)


def file_type_custom():
    picker_type = getattr(ft, "FilePickerFileType", None)
    return picker_type.CUSTOM if picker_type else None


def default_export_dir():
    candidates = [
        os.environ.get("LUUPASS_EXPORT_DIR"),
        os.path.expanduser("~/storage/downloads"),
        "/storage/emulated/0/Download",
        os.path.expanduser("~/Downloads"),
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path

    if "android" in platform.platform().lower():
        return "/storage/emulated/0/Download"
    return os.path.expanduser("~/Downloads")


class Dashboard(ft.Container):
    def __init__(self, vault: Vault, vault_filepath, on_save, on_lock, on_change_password, on_import_vault, on_import_vault_payload=None):
        super().__init__(expand=True, bgcolor=BG)
        self.vault = vault
        self.vault_filepath = vault_filepath
        self.on_save = on_save
        self.on_lock = on_lock
        self.on_change_password = on_change_password
        self.on_import_vault = on_import_vault
        self.on_import_vault_payload = on_import_vault_payload

        self.selected_entry = None
        self.show_settings = False
        self.search_query = ""
        self.pending_import_path = None
        self.pending_import_payload = None
        self.export_dir = default_export_dir()
        self.export_path_field = None
        self.clipboard_clear_timer = None
        self.is_mobile = False
        self.ui_theme = "dark"

        self.export_picker = self.create_file_picker(self.export_result)
        self.export_folder_picker = self.create_file_picker(self.export_folder_result)
        self.import_picker = self.create_file_picker(self.import_result)

        self.content = ft.Container(expand=True, bgcolor=BG)

    def did_mount(self):
        if self.uses_legacy_file_picker():
            self.page.overlay.extend([self.export_picker, self.export_folder_picker, self.import_picker])
        self.page.on_resize = self.handle_resize
        self.page.bgcolor = BG
        self.handle_resize()

    def create_file_picker(self, handler):
        picker = ft.FilePicker()
        try:
            picker.on_result = handler
        except Exception:
            pass
        return picker

    async def maybe_await(self, value):
        if inspect.isawaitable(value):
            return await value
        return value

    def uses_legacy_file_picker(self):
        return not inspect.iscoroutinefunction(self.import_picker.pick_files)

    def show_snack(self, message, bgcolor=None):
        snack_bar = ft.SnackBar(ft.Text(message), bgcolor=bgcolor)
        if hasattr(self.page, "show_snack_bar"):
            self.page.show_snack_bar(snack_bar)
        elif hasattr(self.page, "open"):
            self.page.open(snack_bar)
        elif hasattr(self.page, "show_dialog"):
            self.page.show_dialog(snack_bar)
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
        if hasattr(self.page, "close_dialog"):
            self.page.close_dialog()
        elif hasattr(self.page, "pop_dialog"):
            self.page.pop_dialog()
        elif hasattr(self.page, "close"):
            self.page.close(dialog)
        else:
            dialog.open = False
            self.page.update()

    def handle_resize(self, e=None):
        if not self.page:
            return
        self.is_mobile = self.page.width < 820
        self.content = self.build_mobile_shell() if self.is_mobile else self.build_desktop_shell()
        self.update()

    def refresh(self):
        if self.page:
            self.handle_resize()

    def filtered_entries(self):
        query = self.search_query.strip().lower()
        if not query:
            return list(self.vault.entries)

        matches = []
        for entry in self.vault.entries:
            entry_match = query in (entry.title or "").lower() or query in (entry.url or "").lower()
            account_match = any(query in (account.username or "").lower() for account in entry.accounts)
            if entry_match or account_match:
                matches.append(entry)
        return matches

    def get_offline_favicon(self, title, size=44):
        letter = title[0].upper() if title else "?"
        palette = ["#5865f2", "#6f00be", "#00865c", "#34343d", "#3f4cda", "#005236"]
        color_idx = int(hashlib.md5((title or "").encode("utf-8")).hexdigest(), 16) % len(palette)
        return ft.Container(
            width=size,
            height=size,
            border_radius=12,
            bgcolor=palette[color_idx],
            alignment=alignment_center(),
            content=ft.Text(letter, color=ON_PRIMARY, size=18, weight=ft.FontWeight.BOLD),
        )

    def text_button(self, label, icon, on_click, selected=False):
        return ft.Container(
            height=44,
            border_radius=10,
            bgcolor=PRIMARY_CONTAINER if selected else None,
            padding=padding_symmetric(horizontal=12, vertical=8),
            on_click=on_click,
            content=ft.Row(
                [
                    ft.Icon(icon, size=20, color=ON_PRIMARY if selected else MUTED),
                    ft.Text(label, size=14, weight=ft.FontWeight.W_600, color=ON_PRIMARY if selected else MUTED),
                ],
                spacing=10,
            ),
        )

    def icon_action(self, icon, tooltip, on_click, selected=False):
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=on_click,
            icon_color=ON_PRIMARY if selected else MUTED,
            bgcolor=PRIMARY_CONTAINER if selected else SURFACE_HIGH,
        )

    def search_field(self):
        return ft.TextField(
            hint_text="Search vault...",
            value=self.search_query,
            prefix_icon=ICONS.SEARCH,
            on_change=self.on_search_change,
            border_radius=12,
            bgcolor=SURFACE,
            border_color=OUTLINE,
            focused_border_color=PRIMARY,
            color=TEXT,
            hint_style=ft.TextStyle(color=OUTLINE),
            content_padding=12,
        )

    def build_sidebar(self):
        return ft.Container(
            width=250,
            padding=24,
            bgcolor=SIDEBAR,
            border=border_only(right=ft.BorderSide(1, BORDER)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=42,
                                height=42,
                                border_radius=12,
                                bgcolor=PRIMARY_CONTAINER,
                                alignment=alignment_center(),
                                content=ft.Icon(ICONS.SHIELD, color=ON_PRIMARY, size=24),
                            ),
                            ft.Column(
                                [
                                    ft.Text("LuuPass", size=22, color=TEXT, weight=ft.FontWeight.BOLD),
                                    ft.Text("Offline Vault", size=12, color=MUTED),
                                ],
                                spacing=0,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Container(height=20),
                    ft.Container(
                        padding=16,
                        border_radius=16,
                        bgcolor=SURFACE,
                        border=border_all(1, BORDER),
                        content=ft.Column(
                            [
                                ft.Text("Vault Status", size=12, color=MUTED, weight=ft.FontWeight.W_600),
                                ft.Row(
                                    [
                                        ft.Icon(ICONS.CHECK_CIRCLE, color=SUCCESS, size=18),
                                        ft.Text("Secure", color=TEXT, size=20, weight=ft.FontWeight.W_600),
                                    ],
                                    spacing=8,
                                ),
                                ft.Text(f"{len(self.vault.entries)} total platforms", color=MUTED, size=13),
                            ],
                            spacing=8,
                        ),
                    ),
                    ft.Container(height=18),
                    self.text_button("All Items", ICONS.LIST, lambda e: self.select_entry(None), selected=not self.show_settings and self.selected_entry is None),
                    self.text_button("Add Platform", ICONS.ADD, self.add_new_entry),
                    ft.Container(expand=True),
                    self.text_button("Settings", ICONS.SETTINGS, self.open_settings, selected=self.show_settings),
                    self.text_button("Lock Vault", ICONS.LOCK, lambda e: self.on_lock()),
                ],
                expand=True,
                spacing=8,
            ),
        )

    def build_entry_tile(self, entry):
        selected = self.selected_entry == entry and not self.show_settings
        return ft.Container(
            height=76,
            border_radius=12,
            bgcolor=SURFACE_HIGH if selected else SURFACE,
            border=border_all(1, PRIMARY if selected else BORDER),
            padding=padding_only(left=12, right=12, top=10, bottom=10),
            on_click=lambda e, entry=entry: self.select_entry(entry),
            content=ft.Row(
                [
                    ft.Container(width=3, height=44, border_radius=4, bgcolor=PRIMARY if selected else "transparent"),
                    self.get_offline_favicon(entry.title),
                    ft.Column(
                        [
                            ft.Text(entry.title or "Untitled", size=15, color=TEXT, weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(entry.url or f"{len(entry.accounts)} account(s)", size=12, color=MUTED, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        expand=True,
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text(str(len(entry.accounts)), color=PRIMARY, size=13, weight=ft.FontWeight.W_600),
                ],
                spacing=10,
            ),
        )

    def build_list_panel(self, mobile=False):
        entries = self.filtered_entries()
        list_controls = [self.build_entry_tile(entry) for entry in entries]
        if not list_controls:
            list_controls = [
                ft.Container(
                    expand=True,
                    alignment=alignment_center(),
                    content=ft.Text("No matching items", color=MUTED),
                )
            ]

        header = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Vault", size=28 if mobile else 30, color=TEXT, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{len(self.vault.entries)} platforms protected", size=13, color=MUTED),
                            ],
                            expand=True,
                            spacing=0,
                        ),
                        self.icon_action(ICONS.ADD, "Add Platform", self.add_new_entry),
                        self.icon_action(ICONS.SETTINGS, "Settings", self.open_settings),
                    ],
                    spacing=8,
                ),
                self.search_field(),
            ],
            spacing=14,
        )

        return ft.Container(
            expand=True,
            padding=16 if mobile else 24,
            bgcolor=BG if mobile else SHELL,
            border=border_only(right=ft.BorderSide(1, BORDER)) if not mobile else None,
            content=ft.Column(
                [
                    header,
                    ft.Container(
                        expand=True,
                        content=ft.ListView(list_controls, spacing=8, padding=padding_only(top=6), expand=True),
                    ),
                ],
                expand=True,
                spacing=16,
            ),
        )

    def build_desktop_shell(self):
        return ft.Row(
            [
                self.build_sidebar(),
                ft.Container(width=390, content=self.build_list_panel(mobile=False)),
                ft.Container(expand=True, bgcolor=BG, padding=24, content=self.build_detail_panel()),
            ],
            expand=True,
            spacing=0,
        )

    def build_mobile_shell(self):
        if self.selected_entry or self.show_settings:
            title = "Settings" if self.show_settings else (self.selected_entry.title or "Entry Details")
            return ft.Column(
                [
                    ft.Container(
                        height=64,
                        padding=padding_symmetric(horizontal=12, vertical=8),
                        bgcolor=SHELL,
                        border=border_only(bottom=ft.BorderSide(1, BORDER)),
                        content=ft.Row(
                            [
                                ft.IconButton(icon=ICONS.ARROW_BACK, icon_color=MUTED, on_click=self.go_back),
                                ft.Text(title, color=TEXT, size=18, weight=ft.FontWeight.W_600, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.IconButton(icon=ICONS.LOCK, icon_color=MUTED, tooltip="Lock Vault", on_click=lambda e: self.on_lock()),
                            ],
                        ),
                    ),
                    ft.Container(expand=True, padding=16, bgcolor=BG, content=self.build_detail_panel()),
                ],
                expand=True,
            )

        return ft.Column(
            [
                ft.Container(
                    height=64,
                    padding=padding_symmetric(horizontal=16, vertical=10),
                    bgcolor=SHELL,
                    content=ft.Row(
                        [
                            ft.Text("LuuPass", color=PRIMARY, size=22, weight=ft.FontWeight.BOLD, expand=True),
                            ft.IconButton(icon=ICONS.ADD, icon_color=TEXT, bgcolor=SURFACE_HIGH, on_click=self.add_new_entry),
                            ft.IconButton(icon=ICONS.LOCK, icon_color=MUTED, tooltip="Lock Vault", on_click=lambda e: self.on_lock()),
                        ],
                    ),
                ),
                ft.Container(
                    margin=margin_only(left=16, right=16, top=12, bottom=4),
                    padding=16,
                    border_radius=16,
                    bgcolor=SURFACE,
                    border=border_all(1, BORDER),
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("Vault Status", color=MUTED, size=12, weight=ft.FontWeight.W_600),
                                    ft.Row([ft.Icon(ICONS.CHECK_CIRCLE, color=SUCCESS, size=20), ft.Text("Secure", color=TEXT, size=22, weight=ft.FontWeight.W_600)], spacing=8),
                                ],
                                expand=True,
                                spacing=4,
                            ),
                            ft.Column(
                                [
                                    ft.Text(str(len(self.vault.entries)), color=PRIMARY, size=34, weight=ft.FontWeight.BOLD),
                                    ft.Text("Items", color=MUTED, size=12),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=0,
                            ),
                        ],
                    ),
                ),
                self.build_list_panel(mobile=True),
                ft.Container(
                    height=64,
                    padding=padding_symmetric(horizontal=20, vertical=8),
                    bgcolor=SHELL,
                    border=border_only(top=ft.BorderSide(1, BORDER)),
                    content=ft.Row(
                        [
                            ft.IconButton(icon=ICONS.LIST, icon_color=PRIMARY, tooltip="Vault", on_click=lambda e: self.select_entry(None)),
                            ft.Container(expand=True),
                            ft.IconButton(icon=ICONS.SETTINGS, icon_color=MUTED, tooltip="Settings", on_click=self.open_settings),
                        ],
                    ),
                ),
            ],
            expand=True,
            spacing=0,
        )

    def build_detail_panel(self):
        if self.show_settings:
            return self.build_settings_view()
        if not self.selected_entry:
            return ft.Container(
                expand=True,
                border_radius=18,
                bgcolor=SURFACE,
                border=border_all(1, BORDER),
                alignment=alignment_center(),
                content=ft.Column(
                    [
                        ft.Icon(ICONS.SHIELD, size=56, color=PRIMARY),
                        ft.Text("Select a platform", color=TEXT, size=24, weight=ft.FontWeight.W_600),
                        ft.Text("Choose an item from the vault list to view accounts and notes.", color=MUTED, size=14),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
            )

        return self.build_entry_detail(self.selected_entry)

    def build_entry_detail(self, entry):
        title_field = self.styled_text_field("Platform / Title", entry.title, lambda e: self.update_entry_field(entry, "title", e.control.value), expand=True)
        url_field = self.styled_text_field("URL", entry.url, lambda e: self.update_entry_field(entry, "url", e.control.value), expand=True)
        notes_field = self.styled_text_field("Notes", entry.notes, lambda e: self.update_entry_field(entry, "notes", e.control.value), multiline=True, min_lines=3)

        account_controls = [self.build_account_card(entry, account, index) for index, account in enumerate(entry.accounts)]
        if not account_controls:
            account_controls = [ft.Text("No accounts yet. Add one to store credentials.", color=MUTED)]

        header = ft.Row(
            [
                self.get_offline_favicon(entry.title, size=62),
                ft.Column(
                    [
                        ft.Text(entry.title or "Untitled", size=26, color=TEXT, weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(entry.url or "No URL saved", size=14, color=PRIMARY if entry.url else MUTED, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    expand=True,
                    spacing=3,
                ),
                ft.IconButton(icon=ICONS.DELETE, icon_color=ERROR, tooltip="Delete Platform", on_click=lambda e: self.delete_entry(entry)),
            ],
            spacing=14,
        )

        return ft.Container(
            expand=True,
            border_radius=18,
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            padding=20,
            content=ft.Column(
                [
                    header,
                    ft.Divider(color=BORDER),
                    ft.Column([title_field, url_field], spacing=12) if self.is_mobile else ft.Row([title_field, url_field], spacing=12),
                    ft.Container(height=4),
                    self.section_title("Linked Accounts"),
                    ft.Column(account_controls, spacing=10),
                    flet_button("Add Another Account", icon=ICONS.ADD, on_click=lambda e: self.add_account(entry)),
                    ft.Divider(color=BORDER),
                    notes_field,
                    ft.Row(
                        [
                            ft.Container(expand=True),
                            flet_button("Save Changes", icon=ICONS.SAVE, bgcolor=PRIMARY_CONTAINER, color=ON_PRIMARY, on_click=self.save_current_entry),
                        ],
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
            ),
        )

    def build_account_card(self, entry, account, index):
        username_field = self.styled_text_field("Username / Email", account.username, lambda e: self.update_account_field(account, "username", e.control.value), expand=True)
        password_field = self.styled_text_field(
            "Password",
            account.password,
            lambda e: self.update_account_field(account, "password", e.control.value),
            password=True,
            can_reveal_password=True,
            expand=True,
        )

        username_row = ft.Row([username_field, ft.IconButton(icon=ICONS.COPY, icon_color=PRIMARY, tooltip="Copy Username", on_click=lambda e: self.copy_to_clipboard(username_field.value))], spacing=8)
        password_row = ft.Row([password_field, ft.IconButton(icon=ICONS.COPY, icon_color=PRIMARY, tooltip="Copy Password", on_click=lambda e: self.copy_to_clipboard(password_field.value))], spacing=8)

        return ft.Container(
            padding=16,
            border_radius=14,
            bgcolor=SURFACE_LOW,
            border=border_all(1, BORDER),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row([ft.Icon(ICONS.PERSON, color=PRIMARY, size=18), ft.Text(f"Account {index + 1}", color=TEXT, weight=ft.FontWeight.W_600)], spacing=8),
                            ft.Container(expand=True),
                            ft.IconButton(icon=ICONS.REMOVE_CIRCLE, icon_color=ERROR, tooltip="Remove Account", on_click=lambda e: self.remove_account(entry, account)),
                        ],
                    ),
                    username_row,
                    password_row,
                ],
                spacing=10,
            ),
        )

    def build_settings_view(self):
        self.export_path_field = self.styled_text_field("Export Folder Path", self.export_dir, self.on_export_dir_change, expand=True)

        choose_export_path_btn = ft.IconButton(
            icon=ICONS.FOLDER_OPEN,
            icon_color=PRIMARY,
            bgcolor=SURFACE_HIGH,
            tooltip="Choose Export Folder",
            on_click=self.choose_export_folder,
        )
        export_to_folder_btn = flet_button("Export to Folder", icon=ICONS.DOWNLOAD, on_click=self.export_to_path)
        save_as_label = "Download Vault" if self.page and getattr(self.page, "web", False) else "Save As..."
        save_as_btn = flet_button(save_as_label, icon=ICONS.SAVE, on_click=self.save_as_export)
        import_btn = flet_button("Import Vault", icon=ICONS.UPLOAD, on_click=self.pick_import_vault)
        change_pass_field = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=320, bgcolor=SURFACE_LOW, border_color=OUTLINE, focused_border_color=PRIMARY, color=TEXT)

        def change_pass_clicked(e):
            if change_pass_field.value:
                self.on_change_password(change_pass_field.value)
                change_pass_field.value = ""
                if getattr(change_pass_field, "page", None):
                    change_pass_field.update()
                self.show_snack("Password Changed Successfully!", bgcolor=SUCCESS)

        return ft.Container(
            expand=True,
            border_radius=18,
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            padding=20,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ICONS.SETTINGS, color=PRIMARY, size=30),
                            ft.Column([ft.Text("Settings", color=TEXT, size=26, weight=ft.FontWeight.BOLD), ft.Text("Vault controls and local backup flow", color=MUTED, size=13)], spacing=0),
                        ],
                        spacing=12,
                    ),
                    ft.Divider(color=BORDER),
                    self.section_title("Appearance"),
                    flet_button("Toggle Light/Dark Mode", icon=ICONS.PALETTE, on_click=self.toggle_theme),
                    ft.Container(height=4),
                    self.section_title("Change Master Password"),
                    ft.Column([change_pass_field, flet_button("Change Password", icon=ICONS.PASSWORD, on_click=change_pass_clicked)], spacing=10) if self.is_mobile else ft.Row([change_pass_field, flet_button("Change Password", icon=ICONS.PASSWORD, on_click=change_pass_clicked)], spacing=10),
                    ft.Container(height=4),
                    self.section_title("Data Management"),
                    ft.Text("Import replaces the local vault only after decrypt/parse validation succeeds.", color=MUTED, size=13),
                    ft.Column(
                        [
                            ft.Row([self.export_path_field, choose_export_path_btn], spacing=8),
                            ft.Column([export_to_folder_btn, save_as_btn, import_btn], spacing=8)
                            if self.is_mobile else ft.Row([export_to_folder_btn, save_as_btn, import_btn], spacing=8),
                        ],
                        spacing=10,
                    ),
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor=WARNING_BG,
                        border=border_all(1, WARNING_BORDER),
                        content=ft.Row(
                            [
                                ft.Icon(ICONS.WARNING, color=ERROR, size=20),
                                ft.Text("Do not unlock real vault data on a device that may still be infected.", color=ERROR, size=13, expand=True),
                            ],
                            spacing=10,
                        ),
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=12,
            ),
        )

    def styled_text_field(self, label, value, on_change, expand=False, multiline=False, min_lines=None, password=False, can_reveal_password=False):
        return ft.TextField(
            label=label,
            value=value,
            on_change=on_change,
            expand=expand,
            multiline=multiline,
            min_lines=min_lines,
            password=password,
            can_reveal_password=can_reveal_password,
            border_radius=12,
            bgcolor=SURFACE_LOW,
            border_color=OUTLINE,
            focused_border_color=PRIMARY,
            color=TEXT,
        )

    def section_title(self, text):
        return ft.Text(text, color=MUTED, size=13, weight=ft.FontWeight.W_600)

    def on_search_change(self, e):
        self.search_query = e.control.value
        self.refresh()

    def on_export_dir_change(self, e):
        self.export_dir = e.control.value

    async def choose_export_folder(self, e):
        if getattr(self.page, "web", False):
            self.show_web_filepicker_notice()
            if self.export_path_field and getattr(self.export_path_field, "page", None):
                self.export_path_field.focus()
            return
        picker = self.export_folder_picker if self.uses_legacy_file_picker() else ft.FilePicker()
        result = await self.maybe_await(
            picker.get_directory_path(
                dialog_title="Choose Export Folder",
                initial_directory=self.export_dir or default_export_dir(),
            )
        )
        if result is not None:
            self.export_folder_result(result)

    async def save_as_export(self, e):
        picker_type = file_type_custom()
        kwargs = {
            "dialog_title": "Export Vault",
            "file_name": "vault_backup.luupass",
            "allowed_extensions": ["luupass"],
        }
        if picker_type:
            kwargs["file_type"] = picker_type

        if getattr(self.page, "web", False):
            try:
                with open(self.vault_filepath, "rb") as f:
                    kwargs["src_bytes"] = f.read()
            except Exception as ex:
                self.show_snack(f"Export Error: {ex}", bgcolor=ERROR)
                return
        else:
            kwargs["initial_directory"] = self.export_dir

        picker = self.export_picker if self.uses_legacy_file_picker() else ft.FilePicker()
        try:
            result = await self.maybe_await(picker.save_file(**kwargs))
        except TypeError:
            kwargs.pop("src_bytes", None)
            kwargs.pop("file_type", None)
            result = await self.maybe_await(picker.save_file(**kwargs))

        if getattr(self.page, "web", False):
            self.show_snack("Vault download started.", bgcolor=SUCCESS)
        elif result is not None:
            self.export_result(result)

    async def pick_import_vault(self, e):
        picker_type = file_type_custom()
        kwargs = {
            "allowed_extensions": ["luupass"],
            "allow_multiple": False,
        }
        if picker_type:
            kwargs["file_type"] = picker_type

        if getattr(self.page, "web", False):
            kwargs["with_data"] = True

        picker = self.import_picker if self.uses_legacy_file_picker() else ft.FilePicker()
        try:
            result = await self.maybe_await(picker.pick_files(**kwargs))
        except TypeError:
            kwargs.pop("with_data", None)
            kwargs.pop("file_type", None)
            result = await self.maybe_await(picker.pick_files(**kwargs))
        if result is not None:
            self.import_result(result)

    def show_web_filepicker_notice(self):
        self.show_snack("Browser mode cannot choose folders. Use Download Vault or enter a Termux/server path manually.", bgcolor=ERROR)

    def export_to_path(self, e):
        dest_dir = self.export_dir.strip()
        if not dest_dir:
            self.show_snack("Please enter an export folder path.", bgcolor=ERROR)
            return
        if not os.path.exists(dest_dir):
            self.show_snack(f"Directory not found: {dest_dir}", bgcolor=ERROR)
            return

        dest_file = os.path.join(dest_dir, "vault_backup.luupass")
        try:
            shutil.copy(self.vault_filepath, dest_file)
            self.show_snack(f"Exported to {dest_file}", bgcolor=SUCCESS)
        except Exception as ex:
            self.show_snack(f"Export Error: {ex}", bgcolor=ERROR)

    def export_result(self, e):
        path = e if isinstance(e, str) else getattr(e, "path", None)
        if path:
            try:
                shutil.copy(self.vault_filepath, path)
                self.show_snack("Vault Exported Successfully!", bgcolor=SUCCESS)
            except Exception as ex:
                self.show_snack(f"Export Error: {ex}", bgcolor=ERROR)

    def export_folder_result(self, e):
        path = e if isinstance(e, str) else getattr(e, "path", None)
        if path:
            self.export_dir = path
            if self.export_path_field:
                self.export_path_field.value = path
                self.export_path_field.update()

    def import_result(self, e):
        files = e if isinstance(e, list) else getattr(e, "files", None)
        if files and len(files) > 0:
            selected = files[0]
            self.pending_import_path = getattr(selected, "path", None)
            self.pending_import_payload = getattr(selected, "bytes", None)
            if not self.pending_import_path and not self.pending_import_payload:
                self.show_snack("Selected vault has no readable path/data in this mode.", bgcolor=ERROR)
                return
            self.open_import_password_dialog()

    def open_import_password_dialog(self):
        password_field = ft.TextField(label="Import Vault Password", password=True, can_reveal_password=True, width=320, bgcolor=SURFACE_LOW, border_color=OUTLINE, focused_border_color=PRIMARY, color=TEXT)

        def close_dialog(e=None):
            self.pending_import_path = None
            self.pending_import_payload = None
            self.close_dialog(dialog)

        def confirm_import(e=None):
            if not password_field.value:
                self.show_snack("Please enter the import vault password.", bgcolor=ERROR)
                return
            try:
                if self.pending_import_payload is not None:
                    if not self.on_import_vault_payload:
                        raise ValueError("Import payload handler is not configured.")
                    imported_vault = self.on_import_vault_payload(self.pending_import_payload, password_field.value)
                else:
                    imported_vault = self.on_import_vault(self.pending_import_path, password_field.value)
                password_field.value = ""
                self.pending_import_path = None
                self.pending_import_payload = None
                self.close_dialog(dialog)
                if imported_vault is not None:
                    self.vault = imported_vault
                self.selected_entry = None
                self.show_settings = False
                self.refresh()
                self.show_snack("Vault imported successfully.", bgcolor=SUCCESS)
            except Exception as ex:
                password_field.value = ""
                self.show_snack(f"Import Error: {ex}", bgcolor=ERROR)

        password_field.on_submit = confirm_import
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Validate Import Vault"),
            content=ft.Column([ft.Text("Enter the master password for the selected vault before replacing the current vault."), password_field], tight=True),
            actions=[ft.TextButton("Cancel", on_click=close_dialog), flet_button("Import", icon=ICONS.UPLOAD, on_click=confirm_import)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.show_dialog(dialog)
        password_field.focus()

    def select_entry(self, entry):
        self.show_settings = False
        self.selected_entry = entry
        self.refresh()

    def open_settings(self, e):
        self.show_settings = True
        self.selected_entry = None
        self.refresh()

    def go_back(self, e):
        self.show_settings = False
        self.selected_entry = None
        self.refresh()

    def add_new_entry(self, e):
        new_entry = Entry(title="New Platform", accounts=[Account(username="", password="")])
        self.vault.entries.append(new_entry)
        self.show_settings = False
        self.selected_entry = new_entry
        self.refresh()

    def delete_entry(self, entry):
        self.vault.entries.remove(entry)
        self.selected_entry = None
        self.on_save(self.vault)
        self.refresh()

    def add_account(self, entry):
        entry.accounts.append(Account(username="", password=""))
        self.refresh()

    def remove_account(self, entry, account):
        if account in entry.accounts:
            entry.accounts.remove(account)
            self.refresh()

    def update_entry_field(self, entry, field, value):
        setattr(entry, field, value)

    def update_account_field(self, account, field, value):
        setattr(account, field, value)

    def save_current_entry(self, e):
        self.on_save(self.vault)
        self.refresh()
        self.show_snack("Platform Saved Successfully!", bgcolor=SUCCESS)

    def copy_to_clipboard(self, val):
        self.page.set_clipboard(val)
        self.show_snack("Copied to clipboard! (Auto-clears in 15s)")

        if self.clipboard_clear_timer:
            self.clipboard_clear_timer.cancel()

        def clear_clipboard():
            if self.page and self.clipboard_clear_timer is timer:
                self.page.set_clipboard("")
                self.clipboard_clear_timer = None

        timer = threading.Timer(15.0, clear_clipboard)
        timer.daemon = True
        self.clipboard_clear_timer = timer
        timer.start()

    def toggle_theme(self, e):
        self.ui_theme = "light" if self.ui_theme == "dark" else "dark"
        apply_palette(self.ui_theme)
        self.bgcolor = BG
        if self.page:
            self.page.bgcolor = BG
            self.page.theme_mode = ft.ThemeMode.LIGHT if self.ui_theme == "light" else ft.ThemeMode.DARK
        self.refresh()
