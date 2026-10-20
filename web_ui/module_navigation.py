"""Local module entry routes, separate from household registration state."""

from nicegui import ui

from fg_core.models import FamilyGuildAppState
from fg_core.queries import get_visible_navigation

MODULE_ENTRY_ROUTES: dict[str, str] = {"kidland": "/modules/kidland"}


def render_module_entry(app_state: FamilyGuildAppState, module_key: str) -> None:
    """Render an enabled module's temporary entry, checking current registration."""
    module = next(
        (entry for entry in get_visible_navigation(app_state) if entry.module_key == module_key),
        None,
    )
    if module is None:
        ui.label("This module is not enabled.").mark("module-unavailable")
        return
    with ui.card().classes("w-full").mark(f"module-entry-{module_key}"):
        ui.label(module.display_name.value)
        ui.label("Module views are not connected yet.")
