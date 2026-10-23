"""Trusted member switching shell for the private FamilyGuild MVP."""

from collections.abc import Callable, MutableMapping
from typing import Any

import dbzero as db0
from nicegui import app, events, ui

from fg_core.models import FamilyGuildAppState, Member, MemberRole
from fg_core.queries import get_member_switcher_options, get_visible_navigation, resolve_trusted_member
from web_ui.family_setup import render_initial_setup, render_members_page, render_settings_page
from web_ui.module_navigation import MODULE_ENTRY_ROUTES, render_module_entry

SELECTED_MEMBER_KEY = "selected_member_id"


def build_shell(app_state: FamilyGuildAppState) -> None:
    """Render the minimal FamilyGuild shell for the current browser profile."""

    storage = app.storage.user
    selected_member = _resolve_stored_member(app_state, storage)
    options = {
        db0.uuid(member): _member_option_label(member)
        for member in get_member_switcher_options(app_state)
    }

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4").mark("shell"):
        ui.label("FamilyGuild").classes("text-2xl font-bold")
        family_label = ui.label(app_state.preferences.family_display_name).classes("text-lg")

        member_select = (
            ui.select(
                options=options,
                value=db0.uuid(selected_member) if selected_member is not None else None,
                label="Family member",
                clearable=True,
            )
            .classes("w-full")
            .mark("member-switcher")
        )
        empty_members = ui.label("Add a family member to choose a profile.").mark("empty-members")
        empty_members.set_visibility(not options)
        if not options:
            member_select.disable()

        context_container = ui.column().classes("w-full gap-3").mark("member-context")

        def render_home() -> None:
            """Render the existing minimal family home placeholder."""
            with ui.card().classes("w-full").mark("home-area"):
                ui.label("Family home")

        def render_selected_module(module_key: str) -> None:
            """Resolve current client identity before opening a module entry."""
            if _resolve_stored_member(app_state, storage) is not None:
                render_module_entry(app_state, module_key)

        def bind_module_route(module_key: str) -> Callable[[], None]:
            """Bind a local module key without exposing query-bindable arguments."""
            def render_route() -> None:
                """Render only the module captured by this local route."""
                render_selected_module(module_key)

            return render_route

        def render_member_context() -> None:
            """Refresh member-dependent navigation and the current route."""
            member = _resolve_stored_member(app_state, storage)
            context_container.clear()
            with context_container:
                if member is None:
                    ui.label("Choose a family member to continue.").mark("member-unselected")
                    if not len(app_state.family.members):
                        render_initial_setup(app_state, storage, SELECTED_MEMBER_KEY, refresh_shell)
                    return

                ui.label(f"{member.display_name} · {member.role}").mark("selected-member")
                with ui.row().mark("module-navigation"):
                    ui.link("Home", "/").mark("home-link")
                    for module in get_visible_navigation(app_state):
                        route = MODULE_ENTRY_ROUTES.get(module.module_key)
                        if route is None:
                            ui.label(module.navigation_label.value).mark(
                                f"module-unmapped-{module.module_key}"
                            )
                        else:
                            ui.link(module.navigation_label.value, route).mark(
                                f"module-link-{module.module_key}"
                            )
                if member.role == MemberRole.parent:
                    with ui.card().classes("w-full").mark("parent-only-area"):
                        ui.link("Members", "/members").mark("members-link")
                        ui.link("Settings", "/settings").mark("settings-link")
                ui.sub_pages({
                    "/": render_home,
                    "/members": lambda: render_members_page(
                        app_state, storage, SELECTED_MEMBER_KEY, refresh_shell,
                    ),
                    "/settings": lambda: render_settings_page(
                        app_state, storage, SELECTED_MEMBER_KEY, refresh_shell,
                    ),
                    **{
                        route: bind_module_route(key)
                        for key, route in MODULE_ENTRY_ROUTES.items()
                    },
                })

        def select_member(event: events.ValueChangeEventArguments[Any]) -> None:
            """Resolve client selection and open Home whenever a valid member is chosen."""
            member_id = event.value if isinstance(event.value, str) else None
            member = resolve_trusted_member(app_state, member_id)
            if member is None:
                storage.pop(SELECTED_MEMBER_KEY, None)
                if event.value is not None:
                    member_select.set_value(None)
                    return
            else:
                storage[SELECTED_MEMBER_KEY] = db0.uuid(member)
            render_member_context()
            if member is not None:
                ui.navigate.to("/")

        member_select.on_value_change(select_member)

        def refresh_shell() -> None:
            """Refresh household controls and role-sensitive content after a mutation."""
            synchronize_member()
            render_member_context()

        def synchronize_member() -> None:
            """Refresh current membership options and invalidate stale client selection."""
            current_options = {
                db0.uuid(member): _member_option_label(member)
                for member in get_member_switcher_options(app_state)
            }
            options_changed = member_select.options != current_options
            if options_changed:
                member_select.set_options(current_options)
            member_select.set_enabled(bool(current_options))
            empty_members.set_visibility(not current_options)
            family_label.set_text(app_state.preferences.family_display_name)
            member = _resolve_stored_member(app_state, storage)
            member_id = db0.uuid(member) if member is not None else None
            if member_select.value != member_id:
                member_select.set_value(member_id)
            elif options_changed:
                render_member_context()

        render_member_context()

        # Shared user storage does not refresh controls in other open tabs.
        ui.timer(0.1, synchronize_member)


def _resolve_stored_member(
    app_state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
) -> Member | None:
    """Resolve and, when necessary, clear one client's stored member identifier."""

    stored_id = storage.get(SELECTED_MEMBER_KEY)
    member_id = stored_id if isinstance(stored_id, str) else None
    member = resolve_trusted_member(app_state, member_id)
    if stored_id is not None and member is None:
        storage.pop(SELECTED_MEMBER_KEY, None)
    return member


def _member_option_label(member: Member) -> str:
    """Return the member name and role shown in the trusted switcher."""

    return f"{member.display_name} ({member.role})"
