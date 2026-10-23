"""Minimal private-household setup and parent management forms."""

from collections.abc import Awaitable, Callable, MutableMapping
from functools import partial
from typing import Any

import dbzero as db0
from nicegui import run, ui

from fg_core.commands import (
    add_child_member,
    add_parent_member,
    initialize_household,
    rename_member,
    set_member_active,
    update_preferences,
)
from fg_core.models import FamilyGuildAppState, Member, MemberRole
from fg_core.queries import resolve_trusted_member

Mutation = Callable[[], str | None]
SubmitMutation = Callable[[Mutation], Awaitable[None]]


def render_initial_setup(
    state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
    selection_key: str,
    changed: Callable[[], None],
) -> None:
    """Render empty-household setup and select its first parent in this client.

    The command rechecks household emptiness on submission. Storage is the
    browser-profile mapping; changed refreshes the shell after successful setup.
    """
    with ui.column().mark("setup-bootstrap"):
        preferences = state.preferences
        family_name = ui.input("Family name", value=preferences.family_display_name).mark("family-name")
        currency = ui.input("Currency name", value=preferences.currency_name).mark("currency-name")
        language = ui.select(["en", "pl"], value=preferences.language_preference).mark("language")
        parent_name = ui.input("First parent name", value="").mark("first-parent-name")

        def create_household() -> str:
            """Bind setup inputs and return the new parent's client selection UUID."""
            parent = initialize_household(
                state, family_name.value, parent_name.value, currency.value, language.value,
            )
            return db0.uuid(parent)

        ui.button(
            "Save",
            on_click=lambda: _submit_mutation(
                state, storage, selection_key, changed, create_household, require_parent=False,
            ),
        ).mark("save-preferences")


def render_settings_page(
    state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
    selection_key: str,
    changed: Callable[[], None],
) -> None:
    """Render editable household preferences for the currently resolved parent."""
    if not _is_parent(state, storage, selection_key):
        ui.label("Select an active parent to manage this household.").mark("setup-denied")
        return

    with ui.column().mark("setup-settings"):
        preferences = state.preferences
        family_name = ui.input("Family name", value=preferences.family_display_name).mark("family-name")
        currency = ui.input("Currency name", value=preferences.currency_name).mark("currency-name")
        language = ui.select(["en", "pl"], value=preferences.language_preference).mark("language")

        def save_preferences() -> None:
            """Bind this form's values to the validated preferences command."""
            update_preferences(state, family_name.value, currency.value, language.value)

        ui.button(
            "Save",
            on_click=lambda: _submit_mutation(state, storage, selection_key, changed, save_preferences),
        ).mark("save-preferences")


def render_members_page(
    state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
    selection_key: str,
    changed: Callable[[], None],
) -> None:
    """Render parent-only member creation and active/inactive management rows."""
    if not _is_parent(state, storage, selection_key):
        ui.label("Select an active parent to manage this household.").mark("setup-denied")
        return

    submit = partial(_submit_mutation, state, storage, selection_key, changed)
    with ui.column().mark("setup-members"):
        name = ui.input("Member name", value="").mark("new-member-name")
        role = ui.select(["parent", "child"], value="child").mark("new-member-role")

        def add_member() -> None:
            """Add a member using this form's name and explicitly supported role."""
            if role.value not in {"parent", "child"}:
                raise ValueError("Unsupported member role.")
            command = add_parent_member if role.value == "parent" else add_child_member
            command(state, name.value)

        ui.button("Add member", on_click=lambda: submit(add_member)).mark("add-member")
        for member in state.family.members:
            _render_member_row(state, member, submit)


def _render_member_row(
    state: FamilyGuildAppState, member: Member, submit: SubmitMutation,
) -> None:
    """Bind row controls to a stable UUID rather than a loop variable or name."""
    member_id, active = db0.uuid(member), member.active
    with ui.card().mark(f"manage-{member_id}"):
        ui.label(str(member.role))
        member_name = ui.input("Name", value=member.display_name).mark(f"name-{member_id}")
        ui.button(
            "Rename",
            on_click=lambda: submit(partial(rename_member, state, member_id, member_name.value)),
        ).mark(f"rename-{member_id}")
        ui.button(
            "Deactivate" if active else "Reactivate",
            on_click=lambda: submit(partial(set_member_active, state, member_id, not active)),
        ).mark(f"toggle-{member_id}")


def _is_parent(
    state: FamilyGuildAppState, storage: MutableMapping[str, Any], selection_key: str,
) -> bool:
    """Resolve the current client selection without retaining an earlier role."""
    member = resolve_trusted_member(state, storage.get(selection_key))
    return member is not None and member.role == MemberRole.parent


def _execute_mutation(
    state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
    selection_key: str,
    action: Mutation,
    require_parent: bool,
) -> str | None:
    """Check authority and run a synchronous command in the same atomic worker scope."""
    with db0.atomic():
        if require_parent and not _is_parent(state, storage, selection_key):
            raise ValueError("Select an active parent to continue.")
        return action()


async def _submit_mutation(
    state: FamilyGuildAppState,
    storage: MutableMapping[str, Any],
    selection_key: str,
    changed: Callable[[], None],
    action: Mutation,
    *,
    require_parent: bool = True,
) -> None:
    """Dispatch a checked write, report validation errors, and refresh on success.

    Only initial setup disables the parent check; its command checks household
    emptiness. A returned UUID selects the newly created parent for this client.
    """
    try:
        selected_id = await run.io_bound(
            _execute_mutation, state, storage, selection_key, action, require_parent,
        )
    except ValueError as error:
        ui.notify(str(error), type="negative")
        return
    if selected_id is not None:
        storage[selection_key] = selected_id
    changed()
