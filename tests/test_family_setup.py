"""Exercise setup forms and stale-action authorization using semantic markers."""

import asyncio
from collections.abc import Callable

import dbzero as db0
import httpx
from nicegui import core, events
from nicegui.testing import User, user_simulation

from fg_core.commands import add_parent_member
from fg_core.models import FamilyGuildAppState, Member
from web_ui.shell import build_shell


def set_value(user: User, marker: str, value: str) -> None:
    """Set a marked input as a simulated browser interaction."""
    element = user.find(marker=marker).elements.pop()
    with user:
        element.set_value(value)


def capture_click(user: User, marker: str) -> Callable[[], None]:
    """Retain a real handler to model a queued submission after form removal."""
    button = user.find(marker=marker).elements.pop()
    handler = next(
        listener.handler for listener in button._event_listeners.values()
        if listener.type == "click"
    )

    def invoke() -> None:
        """Dispatch the retained callback with its original client context."""
        with user:
            events.handle_event(handler, events.ClickEventArguments(sender=button, client=button.client))

    return invoke


async def test_bootstrap_from_shell(app_state: FamilyGuildAppState) -> None:
    """An empty household can be prepared and immediately managed without a script."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        set_value(user, "family-name", "Home")
        set_value(user, "first-parent-name", "First")
        set_value(user, "currency-name", "Stars")
        set_value(user, "language", "pl")
        user.find(marker="save-preferences").click()
        await user.should_see(marker="parent-only-area")
        assert len(app_state.family.members) == 1
        assert app_state.preferences.currency_name == "Stars"
        assert app_state.preferences.language_preference == "pl"
        await user.open("/members")
        set_value(user, "new-member-name", "Child")
        user.find(marker="add-member").click()
        await user.should_see(marker=f"manage-{db0.uuid(app_state.family.members[0])}")
        await asyncio.sleep(0.1)
        assert len(app_state.family.members) == 2
        select = user.find(marker="member-switcher").elements.pop()
        assert len(select.options) == 2


async def test_invalid_and_stale_bootstrap(app_state: FamilyGuildAppState) -> None:
    """Blank setup preserves state; a detached bootstrap form cannot reset a family."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        stale_click = capture_click(user, "save-preferences")
        user.find(marker="save-preferences").click()
        await asyncio.sleep(0.1)
        assert len(app_state.family.members) == 0
        set_value(user, "first-parent-name", "First")
        user.find(marker="save-preferences").click()
        await user.should_see(marker="parent-only-area")
        stale_click()
        await asyncio.sleep(0.1)
        assert len(app_state.family.members) == 1


async def test_inactive_actor_cannot_submit_old_form(
    app_state: FamilyGuildAppState, parent_member: Member,
) -> None:
    """A parent deactivated elsewhere loses authority even with an open form."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        set_value(user, "member-switcher", db0.uuid(parent_member))
        await user.open("/members")
        set_value(user, "new-member-name", "Forbidden")
        stale_click = capture_click(user, "add-member")
        parent_member.active = False
        stale_click()
        await asyncio.sleep(0.1)
        assert len(app_state.family.members) == 1


async def test_settings_and_member_management(
    app_state: FamilyGuildAppState, parent_member: Member, child_member: Member,
) -> None:
    """Parents edit preferences and rename/deactivate/reactivate stable members."""
    parent_id, child_id = db0.uuid(parent_member), db0.uuid(child_member)
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        set_value(user, "member-switcher", parent_id)
        await user.open("/settings")
        set_value(user, "family-name", "Edited")
        user.find(marker="save-preferences").click()
        await asyncio.sleep(0.1)
        assert app_state.preferences.family_display_name == "Edited"
        await user.open("/members")
        set_value(user, f"name-{child_id}", "Renamed")
        user.find(marker=f"rename-{child_id}").click()
        await asyncio.sleep(0.1)
        assert child_member.display_name == "Renamed"
        user.find(marker=f"toggle-{child_id}").click()
        await asyncio.sleep(0.1)
        assert not child_member.active
        user.find(marker=f"toggle-{child_id}").click()
        await asyncio.sleep(0.1)
        assert child_member.active
        user.find(marker=f"toggle-{parent_id}").click()
        await asyncio.sleep(0.1)
        assert parent_member.active


async def test_stale_callback_cannot_save_as_child(
    app_state: FamilyGuildAppState, parent_member: Member, child_member: Member,
) -> None:
    """A retained parent form cannot mutate after the browser selects a child."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        set_value(user, "member-switcher", db0.uuid(parent_member))
        await user.open("/settings")
        set_value(user, "family-name", "Forbidden")
        stale_click = capture_click(user, "save-preferences")
        set_value(user, "member-switcher", db0.uuid(child_member))
        stale_click()
        await asyncio.sleep(0.1)
        assert app_state.preferences.family_display_name == "Test Family"
        await user.open("/members")
        await user.should_see(marker="setup-denied")
        await user.should_not_see(marker="add-member")


async def test_self_deactivation_clears_selection(
    app_state: FamilyGuildAppState, parent_member: Member,
) -> None:
    """Self-deactivation with another parent clears role-sensitive controls."""
    await asyncio.to_thread(add_parent_member, app_state, "Other")
    parent_id = db0.uuid(parent_member)
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        set_value(user, "member-switcher", parent_id)
        await user.open("/members")
        user.find(marker=f"toggle-{parent_id}").click()
        await asyncio.sleep(0.1)
        assert not parent_member.active
        await user.should_see(marker="member-unselected")
        await user.should_not_see(marker="parent-only-area")


async def test_management_updates_independent_client(
    app_state: FamilyGuildAppState, parent_member: Member, child_member: Member,
) -> None:
    """Management preserves another client's choice until that member is deactivated."""
    parent_id, child_id = db0.uuid(parent_member), db0.uuid(child_member)
    async with user_simulation(root=lambda: build_shell(app_state)) as parent_user:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app), base_url="http://test",
        ) as client:
            child_user = User(client)
            await parent_user.open("/")
            await child_user.open("/")
            set_value(parent_user, "member-switcher", parent_id)
            set_value(child_user, "member-switcher", child_id)
            await parent_user.open("/members")
            set_value(parent_user, f"name-{child_id}", "Renamed")
            parent_user.find(marker=f"rename-{child_id}").click()
            await asyncio.sleep(0.2)
            child_select = child_user.find(marker="member-switcher").elements.pop()
            assert child_select.value == child_id
            parent_user.find(marker=f"toggle-{child_id}").click()
            await asyncio.sleep(0.2)
            assert child_select.value is None
            parent_select = parent_user.find(marker="member-switcher").elements.pop()
            assert parent_select.value == parent_id
