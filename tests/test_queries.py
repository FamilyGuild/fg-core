from fg_core.commands import add_child_member, configure_dashboard_widget, enable_module
from fg_core.models import CorePreferences, FamilyGuildAppState, ModuleRegistration
from fg_core.queries import (
    get_app_state,
    get_core_preferences,
    get_enabled_modules,
    get_family_summary,
    get_general_dashboard_config,
    get_member_switcher_options,
    get_visible_navigation,
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
