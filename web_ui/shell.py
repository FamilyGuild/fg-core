"""Trusted member switching shell for the private FamilyGuild MVP."""

from collections.abc import MutableMapping
from typing import Any

import dbzero as db0
from nicegui import app, events, ui

from fg_core.models import FamilyGuildAppState, Member, MemberRole
from fg_core.queries import get_member_switcher_options, resolve_trusted_member

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
        ui.label(app_state.preferences.family_display_name).classes("text-lg")

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
        if not options:
            member_select.disable()
            ui.label("Add a family member to choose a profile.").mark("empty-members")

        context_container = ui.column().classes("w-full gap-3").mark("member-context")

        def render_member_context() -> None:
            member = _resolve_stored_member(app_state, storage)
            context_container.clear()
            with context_container:
                if member is None:
                    ui.label("Choose a family member to continue.").mark("member-unselected")
                    return

                ui.label(f"{member.display_name} · {member.role}").mark("selected-member")
                with ui.card().classes("w-full").mark("home-area"):
                    ui.label("Family home")
                if member.role == MemberRole.parent:
                    with ui.card().classes("w-full").mark("parent-only-area"):
                        ui.label("Parent members and settings")

        def select_member(event: events.ValueChangeEventArguments[Any]) -> None:
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

        member_select.on_value_change(select_member)
        render_member_context()

        def synchronize_member() -> None:
            member = _resolve_stored_member(app_state, storage)
            member_id = db0.uuid(member) if member is not None else None
            if member_select.value != member_id:
                member_select.set_value(member_id)

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
