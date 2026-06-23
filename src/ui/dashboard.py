import flet as ft
from src.models import Vault, Entry

class Dashboard(ft.Container):
    def __init__(self, vault: Vault, on_save, on_lock):
        super().__init__(expand=True)
        self.vault = vault
        self.on_save = on_save
        self.on_lock = on_lock
        self.selected_entry = None
        self.entries_list_view = ft.ListView(expand=1, spacing=10, padding=20)
        self.detail_view_container = ft.Container(expand=2, padding=20, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=10)
        self._build_ui()

    def _build_ui(self):
        self.update_list_view()
        self.update_detail_view()

        sidebar = ft.Container(
            content=ft.Column([
                ft.Text("LuuPass", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.TextButton("All Items", icon=ft.icons.LIST, on_click=lambda e: self.select_entry(None)),
                ft.TextButton("Add New", icon=ft.icons.ADD, on_click=self.add_new_entry),
                ft.Divider(),
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

    def update_list_view(self):
        self.entries_list_view.controls.clear()
        for entry in self.vault.entries:
            self.entries_list_view.controls.append(
                ft.ListTile(
                    title=ft.Text(entry.title if entry.title else "Untitled"),
                    subtitle=ft.Text(entry.username),
                    leading=ft.Icon(ft.icons.KEY),
                    on_click=lambda e, entry=entry: self.select_entry(entry),
                    selected=(self.selected_entry == entry)
                )
            )
        if self.page:
            self.entries_list_view.update()

    def select_entry(self, entry):
        self.selected_entry = entry
        self.update_list_view()
        self.update_detail_view()

    def add_new_entry(self, e):
        new_entry = Entry(title="New Item", username="", password="")
        self.vault.entries.append(new_entry)
        self.on_save(self.vault)
        self.select_entry(new_entry)

    def delete_entry(self, entry):
        self.vault.entries.remove(entry)
        self.selected_entry = None
        self.on_save(self.vault)
        self.update_list_view()
        self.update_detail_view()

    def update_detail_view(self):
        if not self.selected_entry:
            self.detail_view_container.content = ft.Container(
                content=ft.Text("Select an item to view details", color=ft.colors.ON_SURFACE_VARIANT),
                alignment=ft.alignment.center
            )
        else:
            entry = self.selected_entry
            title_field = ft.TextField(label="Title", value=entry.title, on_change=lambda e: self.update_field('title', e.control.value))
            user_field = ft.TextField(label="Username", value=entry.username, on_change=lambda e: self.update_field('username', e.control.value), expand=True)
            pass_field = ft.TextField(label="Password", value=entry.password, password=True, can_reveal_password=True, on_change=lambda e: self.update_field('password', e.control.value), expand=True)
            url_field = ft.TextField(label="URL", value=entry.url, on_change=lambda e: self.update_field('url', e.control.value))
            notes_field = ft.TextField(label="Notes", value=entry.notes, multiline=True, on_change=lambda e: self.update_field('notes', e.control.value))

            def copy_to_clipboard(val):
                self.page.set_clipboard(val)
                self.page.snack_bar = ft.SnackBar(ft.Text("Copied to clipboard!"))
                self.page.snack_bar.open = True
                self.page.update()

            self.detail_view_container.content = ft.Column([
                ft.Row([title_field, ft.IconButton(icon=ft.icons.DELETE, icon_color=ft.colors.ERROR, on_click=lambda e: self.delete_entry(entry))]),
                ft.Row([user_field, ft.IconButton(icon=ft.icons.COPY, on_click=lambda e: copy_to_clipboard(user_field.value))]),
                ft.Row([pass_field, ft.IconButton(icon=ft.icons.COPY, on_click=lambda e: copy_to_clipboard(pass_field.value))]),
                url_field,
                notes_field,
            ], scroll=ft.ScrollMode.AUTO)

        if self.page:
            self.detail_view_container.update()

    def update_field(self, field, value):
        if self.selected_entry:
            setattr(self.selected_entry, field, value)
            self.on_save(self.vault)
            if field in ['title', 'username']:
                self.update_list_view()
