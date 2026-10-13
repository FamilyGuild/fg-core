from pathlib import Path

import dbzero as db0

from fg_core.commands import (
    add_child_member,
    add_parent_member,
    configure_dashboard_widget,
    enable_module,
)
from fg_core.models import CorePreferences, FamilyGuildAppState, Member, ModuleRegistration
from fg_core.queries import (
    get_app_state,
    get_core_preferences,
    get_enabled_modules,
    get_family_summary,
    get_general_dashboard_config,
    get_member_switcher_options,
    get_visible_navigation,
    resolve_trusted_member,
)


def test_get_app_state_returns_singleton_root(app_state: FamilyGuildAppState) -> None:
    assert get_app_state() is app_state


def test_get_family_summary(app_state: FamilyGuildAppState) -> None:
    add_child_member(app_state, "Alex")

    assert get_family_summary(app_state) == {
        "household_key": "default",
        "family_display_name": "Test Family",
        "currency_name": "FamCoins",
        "language_preference": "en",
        "member_count": 1,
    }


def test_get_core_preferences(app_state: FamilyGuildAppState) -> None:
    preferences = get_core_preferences(app_state)

    assert isinstance(preferences, CorePreferences)
    assert preferences is app_state.preferences


def test_resolve_trusted_member_returns_active_household_member(
    app_state: FamilyGuildAppState,
) -> None:
    parent = add_parent_member(app_state, "Ada")
    child = add_child_member(app_state, "Alex")

    assert resolve_trusted_member(app_state, db0.uuid(parent)) is parent
    assert resolve_trusted_member(app_state, db0.uuid(child)) is child


def test_resolve_trusted_member_returns_none_without_valid_active_member(
    app_state: FamilyGuildAppState,
) -> None:
    inactive_child = add_child_member(app_state, "Alex")
    inactive_child.active = False
    detached = Member("Riley", inactive_child.role)

    assert resolve_trusted_member(app_state, None) is None
    assert resolve_trusted_member(app_state, "") is None
    assert resolve_trusted_member(app_state, "unknown-member") is None
    assert resolve_trusted_member(app_state, db0.uuid(inactive_child)) is None
    assert resolve_trusted_member(app_state, db0.uuid(detached)) is None


def test_resolve_trusted_member_distinguishes_duplicate_names(
    app_state: FamilyGuildAppState,
) -> None:
    first = add_child_member(app_state, "Alex")
    second = add_child_member(app_state, "Alex")

    assert resolve_trusted_member(app_state, db0.uuid(first)) is first
    assert resolve_trusted_member(app_state, db0.uuid(second)) is second


def test_resolve_trusted_member_after_reopen(
    app_state: FamilyGuildAppState, dbzero_state: Path
) -> None:
    child = add_child_member(app_state, "Alex")
    member_id = db0.uuid(child)
    db0.commit()
    db0.close()
    db0.init(str(dbzero_state / "db0"), prefix="core")

    restored_state = FamilyGuildAppState()
    restored_member = resolve_trusted_member(restored_state, member_id)

    assert restored_member is not None
    assert db0.uuid(restored_member) == member_id


def test_member_switcher_options_include_only_active_members(app_state: FamilyGuildAppState) -> None:
    active_child = add_child_member(app_state, "Alex")
    inactive_child = add_child_member(app_state, "Riley")
    inactive_child.active = False

    assert get_member_switcher_options(app_state) == [active_child]


def test_disabled_modules_are_hidden_from_navigation(
    app_state: FamilyGuildAppState,
    kidland_module: ModuleRegistration,
) -> None:
    disabled_module = enable_module(app_state, "famledger", "FamLedger")
    disabled_module.enabled = False

    assert get_enabled_modules(app_state) == [kidland_module]
    assert get_visible_navigation(app_state) == [kidland_module]


def test_general_dashboard_config_returns_enabled_widgets_ordered(app_state: FamilyGuildAppState) -> None:
    second_widget = configure_dashboard_widget(
        app_state,
        "kidland",
        "recent_activity",
        position=2,
    )
    first_widget = configure_dashboard_widget(
        app_state,
        "kidland",
        "pending_approvals",
        position=1,
    )
    disabled_widget = configure_dashboard_widget(app_state, "kidland", "hidden", position=0)
    disabled_widget.enabled = False

    assert get_general_dashboard_config(app_state) == [first_widget, second_widget]
