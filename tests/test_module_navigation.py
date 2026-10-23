"""Behavioral coverage for locally routed module navigation."""

import asyncio

import dbzero as db0
import httpx
import pytest
from nicegui import core
from nicegui.testing import User
from nicegui.testing import user_simulation

from fg_core.commands import enable_module
from fg_core.models import FamilyGuildAppState, Member, ModuleRegistration
from web_ui.shell import build_shell


async def test_enabled_module_opens_and_returns_home(
    app_state: FamilyGuildAppState, parent_member: Member, kidland_module: ModuleRegistration,
) -> None:
    """A registered enabled module opens through its shell link."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        await user.should_see(marker='module-link-kidland')
        user.find(marker='module-link-kidland').click()
        await user.should_see(marker='module-entry-kidland')
        user.find(marker='home-link').click()
        await user.should_see(marker='home-area')


async def test_disabled_module_cannot_open_directly(
    app_state: FamilyGuildAppState, parent_member: Member, kidland_module: ModuleRegistration,
) -> None:
    """A stale route cannot bypass the current enabled registration state."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        kidland_module.enabled = False
        await user.open('/modules/kidland')
        await user.should_not_see(marker='module-link-kidland')
        await user.should_not_see(marker='module-entry-kidland')
        await user.should_see(marker='module-unavailable')


async def test_direct_entry_requires_selection_and_preserves_it_on_reload(
    app_state: FamilyGuildAppState, child_member: Member, kidland_module: ModuleRegistration,
) -> None:
    """Direct entry reuses and revalidates client member selection."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/modules/kidland')
        await user.should_see(marker='member-unselected')
        await user.should_not_see(marker='module-entry-kidland')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(child_member))
        await user.should_see(marker='home-area')
        assert user.client.sub_pages_router.current_path == '/'
        await user.open('/modules/kidland')
        await user.should_see(marker='module-entry-kidland')
        child_member.active = False
        await user.should_see(marker='member-unselected', retries=20)
        await user.should_not_see(marker='module-entry-kidland')


@pytest.mark.parametrize('kidland_enabled', [False, True])
async def test_query_cannot_override_route_module(
    app_state: FamilyGuildAppState, parent_member: Member, kidland_enabled: bool,
) -> None:
    """Query parameters cannot replace the module bound to a local route."""
    await asyncio.to_thread(enable_module, app_state, 'future', 'Future')
    if kidland_enabled:
        await asyncio.to_thread(enable_module, app_state, 'kidland', 'KidLand')
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        await user.open('/modules/kidland?key=future&module_key=future')
        await user.should_not_see(marker='module-entry-future')
        if kidland_enabled:
            await user.should_see(marker='module-entry-kidland')
        else:
            await user.should_see(marker='module-unavailable')


async def test_unmapped_registration_has_no_link(
    app_state: FamilyGuildAppState, parent_member: Member,
) -> None:
    """Enabled registrations without local integration do not invent routes."""
    await asyncio.to_thread(enable_module, app_state, 'future', 'Future')
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        await user.should_see(marker='module-unmapped-future')
        await user.should_not_see(marker='module-link-future')


@pytest.mark.parametrize('path', ['/modules/kidland', '/unknown'])
async def test_missing_registration_and_unknown_routes(
    app_state: FamilyGuildAppState, parent_member: Member, path: str,
) -> None:
    """Unregistered modules and unknown paths never render module content."""
    async with user_simulation(root=lambda: build_shell(app_state)) as user:
        await user.open('/')
        with user:
            user.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        if path == '/unknown':
            response = await user.http_client.get(path)
            assert response.status_code == 404
            return
        await user.open(path)
        await user.should_not_see(marker='module-entry-kidland')
        await user.should_not_see(marker='home-area')
        if path == '/modules/kidland':
            await user.should_see(marker='module-unavailable')


async def test_module_route_keeps_clients_independent_and_tabs_synchronized(
    app_state: FamilyGuildAppState, parent_member: Member, child_member: Member,
    kidland_module: ModuleRegistration,
) -> None:
    """Routing preserves independent browsers and shared selection across tabs."""
    async with user_simulation(root=lambda: build_shell(app_state)) as parent:
        await parent.open('/modules/kidland')
        with parent:
            parent.find(marker='member-switcher').elements.pop().set_value(db0.uuid(parent_member))
        await parent.should_see(marker='home-area')
        await parent.open('/modules/kidland')
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(core.app), base_url='http://test',
        ) as child_client:
            child = User(child_client)
            await child.open('/modules/kidland')
            with child:
                child.find(marker='member-switcher').elements.pop().set_value(db0.uuid(child_member))
            await child.should_see(marker='home-area')
            await child.open('/modules/kidland')
            await parent.should_see(marker='parent-only-area')
            await child.should_not_see(marker='parent-only-area')
            await child.should_see(marker='module-entry-kidland')
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(core.app), base_url='http://test',
                cookies=parent.http_client.cookies,
            ) as tab_client:
                tab = User(tab_client)
                await tab.open('/')
                with tab:
                    tab.find(marker='member-switcher').elements.pop().set_value(db0.uuid(child_member))
                await parent.should_not_see(marker='parent-only-area', retries=20)
                await parent.should_see(marker='home-area')
                assert parent.client.sub_pages_router.current_path == '/'
                with tab:
                    tab.find(marker='member-switcher').elements.pop().set_value(None)
                await parent.should_see(marker='member-unselected', retries=20)
                await parent.should_not_see(marker='module-entry-kidland')
                await child.should_see(marker='module-entry-kidland')
