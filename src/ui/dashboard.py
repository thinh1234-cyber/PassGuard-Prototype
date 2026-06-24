import hashlib
import inspect
import os
import platform
import shutil
import threading
import asyncio

import flet as ft

from src.models import Account, Entry, Vault
from src.passwords import generate_password
from src.update_checker import check_for_update, github_releases_url
from src.version import APP_VERSION


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


def icon_or(name, fallback):
    return getattr(ICONS, name, fallback)


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
    def __init__(
        self,
        vault: Vault,
        vault_filepath,
        on_save,
        on_lock,
        on_change_password,
        on_import_vault,
        on_import_vault_payload=None,
        on_verify_backups=None,
    ):
        super().__init__(expand=True, bgcolor=BG)
        self.vault = vault
        self.vault_filepath = vault_filepath
        self.on_save = on_save
        self.on_lock = on_lock
        self.on_change_password = on_change_password
        self.on_import_vault = on_import_vault
        self.on_import_vault_payload = on_import_vault_payload
        self.on_verify_backups = on_verify_backups

        self.selected_entry = None
        self.selected_entry_snapshot = None
        self.selected_entry_is_new = False
        self.show_settings = False
        self.search_query = ""
        self.pending_import_path = None
        self.pending_import_payload = None
        self.export_dir = default_export_dir()
        self.export_path_field = None
        self.clipboard_clear_timer = None
        self.idle_lock_timer = None
        self.search_timer = None
        self.is_mobile = False
        self.ui_theme = "dark"
        self.is_dirty = False
        self.is_busy = False
        self.busy_message = ""
        self.idle_lock_seconds = int(os.environ.get("LUUPASS_IDLE_LOCK_SECONDS", "300"))

        self.export_picker = self.create_file_picker(self.export_result)
        self.export_folder_picker = self.create_file_picker(self.export_folder_result)
        self.import_picker = self.create_file_picker(self.import_result)

        self.content = ft.Container(expand=True, bgcolor=BG)

    def did_mount(self):
        page = self.get_page()
        if not page:
            return
        if self.uses_legacy_file_picker():
            page.overlay.extend([self.export_picker, self.export_folder_picker, self.import_picker])
        page.on_resize = self.handle_resize
        page.bgcolor = BG
        self.reset_idle_lock_timer()
        self.handle_resize()

    def will_unmount(self):
        self.clear_clipboard_now()
        self.cancel_timers()

    def get_page(self):
        try:
            return self.page
        except RuntimeError:
            return None

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
        page = self.get_page()
        if not page:
            return
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

    def show_dialog(self, dialog):
        page = self.get_page()
        if not page:
            return
        if hasattr(page, "show_dialog"):
            page.show_dialog(dialog)
        elif hasattr(page, "open"):
            page.open(dialog)
        else:
            page.dialog = dialog
            dialog.open = True
            page.update()

    def close_dialog(self, dialog):
        page = self.get_page()
        if not page:
            return
        if hasattr(page, "close_dialog"):
            page.close_dialog()
        elif hasattr(page, "pop_dialog"):
            page.pop_dialog()
        elif hasattr(page, "close"):
            page.close(dialog)
        else:
            dialog.open = False
            page.update()

    def cancel_timers(self):
        for timer_name in ("clipboard_clear_timer", "idle_lock_timer", "search_timer"):
            timer = getattr(self, timer_name, None)
            if timer:
                timer.cancel()
                setattr(self, timer_name, None)

    async def idle_lock_if_current(self, timer):
        if self.idle_lock_timer is not timer:
            return

        if self.is_dirty:
            self.save_dirty_changes(show_message=False)
        self.show_snack("Vault auto-locked after inactivity.", bgcolor=SUCCESS)
        self.lock_now()

    def reset_idle_lock_timer(self):
        if self.idle_lock_timer:
            self.idle_lock_timer.cancel()

        if self.idle_lock_seconds <= 0:
            self.idle_lock_timer = None
            return

        def auto_lock():
            page = self.get_page()
            if not page or self.idle_lock_timer is not timer:
                return
            if hasattr(page, "run_task"):
                page.run_task(self.idle_lock_if_current, timer)
            else:
                self.lock_now()

        timer = threading.Timer(float(self.idle_lock_seconds), auto_lock)
        timer.daemon = True
        self.idle_lock_timer = timer
        timer.start()

    def record_activity(self):
        self.reset_idle_lock_timer()

    def with_busy_overlay(self, control):
        if not self.is_busy:
            return control

        return ft.Stack(
            [
                control,
                ft.Container(
                    expand=True,
                    bgcolor="#99000000",
                    alignment=alignment_center(),
                    content=ft.Container(
                        padding=20,
                        border_radius=14,
                        bgcolor=SURFACE,
                        border=border_all(1, BORDER),
                        content=ft.Column(
                            [
                                ft.ProgressRing(width=28, height=28, color=PRIMARY),
                                ft.Text(self.busy_message or "Working...", color=TEXT, size=14),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                            spacing=12,
                        ),
                    ),
                ),
            ],
            expand=True,
        )

    def set_busy(self, message=None):
        self.is_busy = message is not None
        self.busy_message = message or ""
        if self.get_page():
            self.handle_resize()

    def handle_resize(self, e=None):
        page = self.get_page()
        if not page:
            return
        self.is_mobile = page.width < 820
        shell = self.build_mobile_shell() if self.is_mobile else self.build_desktop_shell()
        self.content = self.with_busy_overlay(shell)
        self.update()

    def refresh(self):
        if self.get_page():
            self.handle_resize()

    def capture_entry_snapshot(self, entry, is_new=False):
        self.selected_entry = entry
        self.selected_entry_is_new = is_new
        self.selected_entry_snapshot = None if is_new or entry is None else entry.model_dump_json()

    def mark_dirty(self):
        self.is_dirty = True
        self.record_activity()

    def revert_dirty_entry(self):
        if not self.is_dirty or not self.selected_entry:
            self.is_dirty = False
            return

        if self.selected_entry_is_new:
            if self.selected_entry in self.vault.entries:
                self.vault.entries.remove(self.selected_entry)
            self.selected_entry = None
        elif self.selected_entry_snapshot:
            restored = Entry.model_validate_json(self.selected_entry_snapshot)
            self.selected_entry.id = restored.id
            self.selected_entry.title = restored.title
            self.selected_entry.url = restored.url
            self.selected_entry.notes = restored.notes
            self.selected_entry.accounts = restored.accounts

        self.is_dirty = False
        self.selected_entry_snapshot = None
        self.selected_entry_is_new = False

    def save_dirty_changes(self, show_message=True):
        if not self.is_dirty:
            return

        self.on_save(self.vault)
        self.is_dirty = False
        self.selected_entry_snapshot = self.selected_entry.model_dump_json() if self.selected_entry else None
        self.selected_entry_is_new = False
        if show_message:
            self.show_snack("Changes saved.", bgcolor=SUCCESS)

    def guard_dirty(self, action, title="Unsaved Changes"):
        if not self.is_dirty:
            action()
            return

        def save_and_continue(e=None):
            self.save_dirty_changes(show_message=False)
            self.close_dialog(dialog)
            action()

        def discard_and_continue(e=None):
            self.revert_dirty_entry()
            self.close_dialog(dialog)
            action()

        def cancel(e=None):
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text("Save changes before leaving this item?"),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Discard", on_click=discard_and_continue),
                flet_button("Save", icon=ICONS.SAVE, on_click=save_and_continue),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.show_dialog(dialog)

    def lock_now(self):
        self.clear_clipboard_now()
        self.cancel_timers()
        self.on_lock()

    def request_lock(self, e=None):
        self.record_activity()

        def lock_after_save():
            self.lock_now()

        self.guard_dirty(lock_after_save, title="Lock Vault")

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
            height=48,
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
            width=48,
            height=48,
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
                    self.text_button("Lock Vault", ICONS.LOCK, self.request_lock),
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
                        content=ft.ListView(list_controls, spacing=8, item_extent=84, cache_extent=420, padding=padding_only(top=6), expand=True),
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
                                ft.IconButton(icon=ICONS.LOCK, icon_color=MUTED, tooltip="Lock Vault", on_click=self.request_lock, width=48, height=48),
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
                            ft.IconButton(icon=ICONS.ADD, icon_color=TEXT, bgcolor=SURFACE_HIGH, on_click=self.add_new_entry, width=48, height=48),
                            ft.IconButton(icon=ICONS.LOCK, icon_color=MUTED, tooltip="Lock Vault", on_click=self.request_lock, width=48, height=48),
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
                            ft.IconButton(icon=ICONS.LIST, icon_color=PRIMARY, tooltip="Vault", on_click=lambda e: self.select_entry(None), width=56, height=48),
                            ft.Container(expand=True),
                            ft.IconButton(icon=ICONS.SETTINGS, icon_color=MUTED, tooltip="Settings", on_click=self.open_settings, width=56, height=48),
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
        dirty_indicator = ft.Container(
            padding=padding_symmetric(horizontal=10, vertical=6),
            border_radius=999,
            bgcolor=WARNING_BG,
            border=border_all(1, WARNING_BORDER),
            content=ft.Text("Unsaved changes", color=ERROR, size=12, weight=ft.FontWeight.W_600),
        ) if self.is_dirty else ft.Container()

        return ft.Container(
            expand=True,
            border_radius=18,
            bgcolor=SURFACE,
            border=border_all(1, BORDER),
            padding=20,
            content=ft.Column(
                [
                    header,
                    dirty_indicator,
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

        async def copy_username(e):
            await self.copy_to_clipboard(username_field.value)

        async def copy_password(e):
            await self.copy_to_clipboard(password_field.value)

        def generate_for_account(e):
            password = generate_password()
            account.password = password
            password_field.value = password
            self.mark_dirty()
            if getattr(password_field, "page", None):
                password_field.update()
            self.show_snack("Password generated. Save changes to persist it.", bgcolor=SUCCESS)

        username_row = ft.Row(
            [
                username_field,
                ft.IconButton(icon=ICONS.COPY, icon_color=PRIMARY, tooltip="Copy Username", on_click=copy_username, width=48, height=48),
            ],
            spacing=8,
        )
        password_row = ft.Row(
            [
                password_field,
                ft.IconButton(icon=ICONS.PASSWORD, icon_color=PRIMARY, tooltip="Generate Password", on_click=generate_for_account, width=48, height=48),
                ft.IconButton(icon=ICONS.COPY, icon_color=PRIMARY, tooltip="Copy Password", on_click=copy_password, width=48, height=48),
            ],
            spacing=8,
        )

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
                            ft.IconButton(icon=ICONS.REMOVE_CIRCLE, icon_color=ERROR, tooltip="Remove Account", on_click=lambda e: self.remove_account(entry, account), width=48, height=48),
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
        page = self.get_page()
        save_as_label = "Download Vault" if page and getattr(page, "web", False) else "Save As..."
        save_as_btn = flet_button(save_as_label, icon=ICONS.SAVE, on_click=self.save_as_export)
        import_btn = flet_button("Import Vault", icon=ICONS.UPLOAD, on_click=self.pick_import_vault)
        verify_backups_btn = flet_button("Verify Backups", icon=ICONS.CHECK_CIRCLE, on_click=self.run_backup_diagnostics)
        check_updates_btn = flet_button("Check Updates", icon=icon_or("UPDATE", icon_or("REFRESH", ICONS.SETTINGS)), on_click=self.check_updates)
        current_pass_field = ft.TextField(label="Current Password", password=True, can_reveal_password=True, width=320, bgcolor=SURFACE_LOW, border_color=OUTLINE, focused_border_color=PRIMARY, color=TEXT)
        new_pass_field = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=320, bgcolor=SURFACE_LOW, border_color=OUTLINE, focused_border_color=PRIMARY, color=TEXT)
        confirm_pass_field = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True, width=320, bgcolor=SURFACE_LOW, border_color=OUTLINE, focused_border_color=PRIMARY, color=TEXT)

        def change_pass_clicked(e):
            self.record_activity()
            if not current_pass_field.value or not new_pass_field.value or not confirm_pass_field.value:
                self.show_snack("Please fill all password fields.", bgcolor=ERROR)
                return
            if new_pass_field.value != confirm_pass_field.value:
                self.show_snack("New password confirmation does not match.", bgcolor=ERROR)
                return
            if len(new_pass_field.value) < 8:
                self.show_snack("New password must be at least 8 characters.", bgcolor=ERROR)
                return

            try:
                self.on_change_password(current_pass_field.value, new_pass_field.value, self.vault)
                self.is_dirty = False
                self.selected_entry_snapshot = self.selected_entry.model_dump_json() if self.selected_entry else None
                self.selected_entry_is_new = False
                for field in (current_pass_field, new_pass_field, confirm_pass_field):
                    field.value = ""
                    if getattr(field, "page", None):
                        field.update()
                self.show_snack("Password Changed Successfully!", bgcolor=SUCCESS)
            except Exception as ex:
                self.show_snack(f"Password change failed: {ex}", bgcolor=ERROR)

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
                    ft.Text(f"LuuPass v{APP_VERSION}", color=MUTED, size=13),
                    ft.Column([flet_button("Toggle Light/Dark Mode", icon=ICONS.PALETTE, on_click=self.toggle_theme), check_updates_btn], spacing=8)
                    if self.is_mobile else ft.Row([flet_button("Toggle Light/Dark Mode", icon=ICONS.PALETTE, on_click=self.toggle_theme), check_updates_btn], spacing=8),
                    ft.Container(height=4),
                    self.section_title("Change Master Password"),
                    ft.Column(
                        [
                            current_pass_field,
                            new_pass_field,
                            confirm_pass_field,
                            flet_button("Change Password", icon=ICONS.PASSWORD, on_click=change_pass_clicked),
                        ],
                        spacing=10,
                    ),
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
                    self.section_title("Vault Diagnostics"),
                    ft.Text(self.vault_summary_text(), color=MUTED, size=13, selectable=True),
                    verify_backups_btn,
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

    def vault_summary_text(self):
        backup_count = sum(1 for i in range(1, 4) if os.path.exists(f"{self.vault_filepath}.bak{i}"))
        vault_exists = os.path.exists(self.vault_filepath)
        try:
            size = os.path.getsize(self.vault_filepath) if vault_exists else 0
        except OSError:
            size = 0
        return f"Vault: {self.vault_filepath}\nEntries: {len(self.vault.entries)}\nBackups: {backup_count}/3\nSize: {size} bytes"

    def run_backup_diagnostics(self, e=None):
        self.record_activity()
        if not self.on_verify_backups:
            self.show_snack("Backup verifier is not configured.", bgcolor=ERROR)
            return

        try:
            results = self.on_verify_backups()
        except Exception as ex:
            self.show_snack(f"Backup verification failed: {ex}", bgcolor=ERROR)
            return

        lines = []
        for result in results:
            name = os.path.basename(result["path"])
            if not result["exists"]:
                lines.append(f"{name}: missing")
            elif result["valid"]:
                lines.append(f"{name}: OK ({result.get('entries', 0)} entries)")
            else:
                lines.append(f"{name}: INVALID")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Backup Diagnostics"),
            content=ft.Text("\n".join(lines) or "No backup slots found.", selectable=True),
            actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.show_dialog(dialog)

    async def check_updates(self, e=None):
        self.record_activity()
        self.set_busy("Checking for updates...")
        try:
            result = await asyncio.to_thread(check_for_update)
        except Exception as ex:
            self.show_snack(f"Update check failed: {ex}", bgcolor=ERROR)
            return
        finally:
            self.set_busy(None)

        release = result.latest_release
        if result.source == "git-head":
            if result.update_available:
                message = (
                    "Remote repository has newer code.\n"
                    f"Local HEAD: {result.local_commit[:12] if result.local_commit else 'unknown'}\n"
                    f"Remote HEAD: {result.remote_commit[:12] if result.remote_commit else 'unknown'}"
                )
            else:
                message = (
                    "No newer remote commit detected.\n"
                    f"Current version: {APP_VERSION}\n"
                    f"Remote HEAD: {result.remote_commit[:12] if result.remote_commit else 'unknown'}"
                )
        elif result.update_available:
            message = f"Update available: {release.version.normalized}\n{release.html_url}"
        else:
            message = f"LuuPass is up to date.\nCurrent: {APP_VERSION}\nLatest: {release.version.normalized}"

        def open_releases(e=None):
            page = self.get_page()
            if page and hasattr(page, "launch_url"):
                page.launch_url(release.html_url or github_releases_url())
            self.close_dialog(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Update Check"),
            content=ft.Text(message, selectable=True),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog)),
                flet_button("Open Remote", icon=icon_or("OPEN_IN_NEW", icon_or("LINK", ICONS.SETTINGS)), on_click=open_releases),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.show_dialog(dialog)

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
        self.record_activity()
        if self.search_timer:
            self.search_timer.cancel()

        def refresh_search():
            page = self.get_page()
            if not page or self.search_timer is not timer:
                return
            if hasattr(page, "run_task"):
                page.run_task(self.refresh_after_search, timer)
            else:
                self.refresh()

        timer = threading.Timer(0.2, refresh_search)
        timer.daemon = True
        self.search_timer = timer
        timer.start()

    async def refresh_after_search(self, timer):
        if self.search_timer is timer:
            self.search_timer = None
            self.refresh()

    def on_export_dir_change(self, e):
        self.export_dir = e.control.value
        self.record_activity()

    async def choose_export_folder(self, e):
        page = self.get_page()
        if page and getattr(page, "web", False):
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

        page = self.get_page()
        if page and getattr(page, "web", False):
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

        if page and getattr(page, "web", False):
            self.show_snack("Vault download started.", bgcolor=SUCCESS)
        elif result is not None:
            self.export_result(result)

    async def pick_import_vault(self, e):
        if self.is_dirty:
            def continue_import():
                page = self.get_page()
                if page and hasattr(page, "run_task"):
                    page.run_task(self.pick_import_vault, e)

            self.guard_dirty(continue_import, title="Import Vault")
            return

        picker_type = file_type_custom()
        kwargs = {
            "allowed_extensions": ["luupass"],
            "allow_multiple": False,
        }
        if picker_type:
            kwargs["file_type"] = picker_type

        page = self.get_page()
        if page and getattr(page, "web", False):
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
                self.capture_entry_snapshot(None)
                self.is_dirty = False
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
        self.record_activity()

        def do_select():
            self.show_settings = False
            self.capture_entry_snapshot(entry)
            self.refresh()

        self.guard_dirty(do_select)

    def open_settings(self, e):
        self.record_activity()

        def do_open_settings():
            self.show_settings = True
            self.capture_entry_snapshot(None)
            self.refresh()

        self.guard_dirty(do_open_settings)

    def go_back(self, e):
        self.record_activity()

        def do_back():
            self.show_settings = False
            self.capture_entry_snapshot(None)
            self.refresh()

        self.guard_dirty(do_back)

    def add_new_entry(self, e):
        self.record_activity()

        def do_add():
            new_entry = Entry(title="New Platform", accounts=[Account(username="", password="")])
            self.vault.entries.append(new_entry)
            self.show_settings = False
            self.capture_entry_snapshot(new_entry, is_new=True)
            self.is_dirty = True
            self.refresh()

        self.guard_dirty(do_add)

    def delete_entry(self, entry):
        self.record_activity()
        self.vault.entries.remove(entry)
        self.capture_entry_snapshot(None)
        self.is_dirty = False
        self.on_save(self.vault)
        self.refresh()

    def add_account(self, entry):
        self.record_activity()
        entry.accounts.append(Account(username="", password=""))
        self.mark_dirty()
        self.refresh()

    def remove_account(self, entry, account):
        self.record_activity()
        if account in entry.accounts:
            entry.accounts.remove(account)
            self.mark_dirty()
            self.refresh()

    def update_entry_field(self, entry, field, value):
        self.record_activity()
        setattr(entry, field, value)
        self.mark_dirty()

    def update_account_field(self, account, field, value):
        self.record_activity()
        setattr(account, field, value)
        self.mark_dirty()

    def save_current_entry(self, e):
        self.record_activity()
        self.save_dirty_changes(show_message=False)
        self.refresh()
        self.show_snack("Platform Saved Successfully!", bgcolor=SUCCESS)

    async def set_clipboard_text(self, val):
        text = "" if val is None else str(val)
        errors = []

        clipboard_service = getattr(ft, "Clipboard", None)
        if clipboard_service:
            try:
                await self.maybe_await(clipboard_service().set(text))
                return
            except Exception as ex:
                errors.append(ex)

        page = self.get_page()
        if page and hasattr(page, "set_clipboard"):
            try:
                await self.maybe_await(page.set_clipboard(text))
                return
            except Exception as ex:
                errors.append(ex)

        if page and hasattr(page, "set_clipboard_async"):
            try:
                await self.maybe_await(page.set_clipboard_async(text))
                return
            except Exception as ex:
                errors.append(ex)

        if errors:
            raise errors[-1]
        raise RuntimeError("Clipboard API is not available.")

    async def clear_clipboard_if_current(self, timer):
        if self.clipboard_clear_timer is not timer:
            return

        try:
            await self.set_clipboard_text("")
        except Exception:
            pass
        finally:
            if self.clipboard_clear_timer is timer:
                self.clipboard_clear_timer = None

    def clear_clipboard_now(self):
        page = self.get_page()
        if not page:
            return
        if hasattr(page, "run_task"):
            try:
                page.run_task(self.set_clipboard_text, "")
                return
            except Exception:
                pass
        if hasattr(page, "set_clipboard"):
            try:
                page.set_clipboard("")
            except Exception:
                pass

    def schedule_clipboard_clear(self):
        if self.clipboard_clear_timer:
            self.clipboard_clear_timer.cancel()

        def clear_clipboard():
            page = self.get_page()
            if not page or self.clipboard_clear_timer is not timer:
                return
            if hasattr(page, "run_task"):
                page.run_task(self.clear_clipboard_if_current, timer)
                return
            try:
                page.set_clipboard("")
            finally:
                if self.clipboard_clear_timer is timer:
                    self.clipboard_clear_timer = None

        timer = threading.Timer(15.0, clear_clipboard)
        timer.daemon = True
        self.clipboard_clear_timer = timer
        timer.start()

    async def copy_to_clipboard(self, val):
        try:
            await self.set_clipboard_text(val)
        except Exception:
            self.show_snack("Clipboard access was blocked by the browser.", bgcolor=ERROR)
            return

        message = "Copied to clipboard! (Auto-clears in 15s)"
        page = self.get_page()
        if page and getattr(page, "web", False):
            message = "Copied to clipboard! (Auto-clear is best-effort in browser mode)"
        self.show_snack(message)
        self.schedule_clipboard_clear()

    def toggle_theme(self, e):
        self.ui_theme = "light" if self.ui_theme == "dark" else "dark"
        apply_palette(self.ui_theme)
        self.bgcolor = BG
        page = self.get_page()
        if page:
            page.bgcolor = BG
            page.theme_mode = ft.ThemeMode.LIGHT if self.ui_theme == "light" else ft.ThemeMode.DARK
        self.refresh()
