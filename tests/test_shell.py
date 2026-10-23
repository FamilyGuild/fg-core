import asyncio

import dbzero as db0
import httpx
import pytest
from nicegui import app, core, ui
from nicegui.testing import User, user_simulation

from fg_core.models import FamilyGuildAppState, Member
from web_ui.shell import SELECTED_MEMBER_KEY, build_shell


@pytest.mark.parametrize("path", ["/members", "/settings", "/modules/kidland"])
@pytest.mark.parametrize("target_role", ["parent", "child"])
async def test_member_selection_opens_home(
    app_state: FamilyGuildAppState,
    parent_member: Member,
    child_member: Member,
    path: str,
    target_role: str,
) -> None:
    """Every valid profile selection leaves the previous route and opens Home."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        _select_member(user, db0.uuid(parent_member))
        await user.should_see(marker="home-area")
        await user.open(path)
        await user.should_not_see(marker="home-area")
        if target_role == "parent":
            _select_member(user, db0.uuid(child_member))
            await user.should_not_see(marker="parent-only-area")
            await user.open(path)
        target = parent_member if target_role == "parent" else child_member
        _select_member(user, db0.uuid(target))
        await user.should_see(marker="home-area")
        assert user.client.sub_pages_router.current_path == "/"
        await user.should_not_see(marker="setup-denied")


def _select_member(user: User, member_id: str | None) -> None:
    select = user.find(marker="member-switcher").elements.pop()
    assert isinstance(select, ui.select)
    with user:
        select.value = member_id


def _selected_member_id(user: User) -> str | None:
    select = user.find(marker="member-switcher").elements.pop()
    assert isinstance(select, ui.select)
    return select.value


async def test_empty_household_is_safe(app_state: FamilyGuildAppState) -> None:
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")

        await user.should_see(marker="empty-members")
        await user.should_see(marker="member-unselected")
        await user.should_not_see(marker="parent-only-area")
        select = user.find(marker="member-switcher").elements.pop()
        assert isinstance(select, ui.select)
        assert select.enabled is False


async def test_parent_and_child_can_be_selected_independently(
    app_state: FamilyGuildAppState,
    parent_member: Member,
    child_member: Member,
) -> None:
    parent_id = db0.uuid(parent_member)
    child_id = db0.uuid(child_member)

    async with user_simulation(root=lambda: build_shell(app_state)) as parent_user:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app), base_url="http://test"
        ) as client:
            child_user = User(client)
            await parent_user.open("/")
            await child_user.open("/")

            parent_select = parent_user.find(marker="member-switcher").elements.pop()
            assert isinstance(parent_select, ui.select)
            assert set(parent_select.options) == {parent_id, child_id}

            _select_member(parent_user, parent_id)
            _select_member(child_user, child_id)
            await asyncio.sleep(0.2)

            await parent_user.should_see(marker="parent-only-area")
            await child_user.should_not_see(marker="parent-only-area")
            assert _selected_member_id(parent_user) == parent_id
            assert _selected_member_id(child_user) == child_id

            await parent_user.open("/")
            await child_user.open("/")
            assert _selected_member_id(parent_user) == parent_id
            assert _selected_member_id(child_user) == child_id


async def test_switching_from_parent_to_child_removes_parent_area(
    app_state: FamilyGuildAppState,
    parent_member: Member,
    child_member: Member,
) -> None:
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        _select_member(user, db0.uuid(parent_member))
        await user.should_see(marker="parent-only-area")

        _select_member(user, db0.uuid(child_member))
        await user.should_not_see(marker="parent-only-area")
        await user.should_see(marker="selected-member")


async def test_stale_selection_is_cleared_on_reload(
    app_state: FamilyGuildAppState,
    parent_member: Member,
) -> None:
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        _select_member(user, db0.uuid(parent_member))
        await user.should_see(marker="parent-only-area")

        parent_member.active = False
        await user.open("/")

        assert _selected_member_id(user) is None
        await user.should_see(marker="member-unselected")
        await user.should_not_see(marker="parent-only-area")


async def test_duplicate_names_use_distinct_member_ids(
    app_state: FamilyGuildAppState,
    duplicate_child_members: tuple[Member, Member],
) -> None:
    first, second = duplicate_child_members
    first_id = db0.uuid(first)
    second_id = db0.uuid(second)

    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        select = user.find(marker="member-switcher").elements.pop()
        assert isinstance(select, ui.select)
        assert set(select.options) == {first_id, second_id}

        _select_member(user, second_id)
        await user.open("/")

        assert _selected_member_id(user) == second_id


async def test_unknown_selection_leaves_client_unselected(
    app_state: FamilyGuildAppState,
    parent_member: Member,
) -> None:
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        _select_member(user, db0.uuid(parent_member))
        await user.should_see(marker="parent-only-area")

        _select_member(user, "unknown-member")

        assert _selected_member_id(user) is None
        await user.should_see(marker="member-unselected")
        await user.should_not_see(marker="parent-only-area")


async def test_unknown_stored_selection_is_cleared_on_page_load(
    app_state: FamilyGuildAppState,
) -> None:
    def build_shell_with_stale_storage() -> None:
        app.storage.user[SELECTED_MEMBER_KEY] = "unknown-member"
        build_shell(app_state)

    async with user_simulation(root=build_shell_with_stale_storage) as user:
        await user.open("/")

        assert _selected_member_id(user) is None
        await user.should_see(marker="member-unselected")
        await user.should_not_see(marker="parent-only-area")


async def test_tabs_with_the_same_browser_identity_share_selection(
    app_state: FamilyGuildAppState,
    parent_member: Member,
) -> None:
    parent_id = db0.uuid(parent_member)

    async with user_simulation(root=lambda: build_shell(app_state)) as first_tab:
        await first_tab.open("/")
        _select_member(first_tab, parent_id)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app),
            base_url="http://test",
            cookies=first_tab.http_client.cookies,
        ) as client:
            second_tab = User(client)
            await second_tab.open("/")

            assert _selected_member_id(second_tab) == parent_id
            await second_tab.should_see(marker="parent-only-area")


async def test_open_tabs_synchronize_switching_and_clearing(
    app_state: FamilyGuildAppState,
    parent_member: Member,
    child_member: Member,
) -> None:
    parent_id = db0.uuid(parent_member)
    child_id = db0.uuid(child_member)

    async with user_simulation(root=lambda: build_shell(app_state)) as first_tab:
        await first_tab.open("/")
        _select_member(first_tab, parent_id)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app),
            base_url="http://test",
            cookies=first_tab.http_client.cookies,
        ) as client:
            second_tab = User(client)
            await second_tab.open("/")
            _select_member(second_tab, child_id)

            await first_tab.should_not_see(marker="parent-only-area", retries=20)
            assert _selected_member_id(first_tab) == child_id
            assert _selected_member_id(second_tab) == child_id

            _select_member(first_tab, parent_id)
            await second_tab.should_see(marker="parent-only-area", retries=20)
            assert _selected_member_id(second_tab) == parent_id

            _select_member(second_tab, None)
            await first_tab.should_see(marker="member-unselected", retries=20)
            await first_tab.should_not_see(marker="parent-only-area")
            assert _selected_member_id(first_tab) is None
            assert _selected_member_id(second_tab) is None


async def test_open_tab_clears_deactivated_member_without_reload(
    app_state: FamilyGuildAppState,
    parent_member: Member,
) -> None:
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open("/")
        _select_member(user, db0.uuid(parent_member))
        await user.should_see(marker="parent-only-area")

        parent_member.active = False

        await user.should_see(marker="member-unselected", retries=20)
        await user.should_not_see(marker="parent-only-area")
        assert _selected_member_id(user) is None
        with user:
            assert SELECTED_MEMBER_KEY not in app.storage.user
