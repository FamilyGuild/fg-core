from datetime import UTC, datetime

import pytest

from fg_core.commands import (
    add_child_member,
    add_parent_member,
    configure_dashboard_widget,
    create_family,
    enable_module,
    switch_active_member,
)
from fg_core.models import CorePreferences, FamilyGuildAppState, Member
from fg_core.queries import get_active_member


def test_create_family_initializes_singleton_root() -> None:
    app_state = create_family("Guild House")

    assert isinstance(app_state, FamilyGuildAppState)
    assert app_state is FamilyGuildAppState()
    assert app_state.family.household_key == "default"
    assert isinstance(app_state.preferences, CorePreferences)
    assert app_state.preferences.family_display_name == "Guild House"
    assert app_state.preferences.currency_name == "FamCoins"
    assert app_state.preferences.language_preference == "en"
    assert app_state.active_member_state.active_member is None
    assert app_state.active_member_state.last_switched_at is None


def test_app_state_has_single_family_reference_not_family_collection() -> None:
    app_state = create_family("Guild House")

    assert hasattr(app_state, "family")
    assert not hasattr(app_state, "families")
    assert list(app_state.family.members) == []
    assert list(app_state.family.enabled_modules) == []
    assert list(app_state.family.dashboard_widgets) == []


def test_family_does_not_own_core_preferences() -> None:
    app_state = create_family("Guild House")

    assert not hasattr(app_state.family, "currency_name")
    assert not hasattr(app_state.family, "language_preference")
    assert not hasattr(app_state.family, "family_display_name")


def test_create_family_can_set_core_preferences() -> None:
    app_state = create_family(
        "Guild House",
        currency_name="Stars",
        language_preference="pl",
        household_key="founder-family",
    )

    assert app_state.family.household_key == "founder-family"
    assert app_state.preferences.family_display_name == "Guild House"
    assert app_state.preferences.currency_name == "Stars"
    assert app_state.preferences.language_preference == "pl"


def test_add_parent_member(app_state: FamilyGuildAppState) -> None:
    parent = add_parent_member(app_state, "Ada")

    assert parent.display_name == "Ada"
    assert parent.role == "parent"
    assert parent.active is True
    assert parent in app_state.family.members


def test_add_child_member(app_state: FamilyGuildAppState) -> None:
    child = add_child_member(app_state, "Alex", kid_profile_ref="kid-profile-1")

    assert child.display_name == "Alex"
    assert child.role == "child"
    assert child.active is True
    assert child.kid_profile_ref == "kid-profile-1"
    assert child in app_state.family.members


def test_switch_active_member_changes_active_member(app_state: FamilyGuildAppState) -> None:
    parent = add_parent_member(app_state, "Ada")
    switched_at = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)

    active_state = switch_active_member(app_state, parent, switched_at=switched_at)

    assert active_state.active_member is parent
    assert active_state.last_switched_at == switched_at
    assert get_active_member(app_state) is parent


def test_switch_rejects_inactive_member(app_state: FamilyGuildAppState) -> None:
    parent = add_parent_member(app_state, "Ada")
    child = add_child_member(app_state, "Alex")
    switch_active_member(app_state, parent)
    child.active = False

    with pytest.raises(ValueError, match="inactive"):
        switch_active_member(app_state, child)

    assert get_active_member(app_state) is parent


def test_switch_rejects_unknown_member(app_state: FamilyGuildAppState) -> None:
    parent = add_parent_member(app_state, "Ada")
    switch_active_member(app_state, parent)
    unknown_child = Member("Riley", "child")

    with pytest.raises(ValueError, match="belong"):
        switch_active_member(app_state, unknown_child)

    assert get_active_member(app_state) is parent


def test_enable_kidland_module(app_state: FamilyGuildAppState) -> None:
    module = enable_module(app_state, "kidland", "KidLand")

    assert module.module_key == "kidland"
    assert module.enabled is True
    assert module.display_name.value == "KidLand"
    assert module.navigation_label.value == "KidLand"
    assert module in app_state.family.enabled_modules


def test_enable_module_reenables_existing_module(app_state: FamilyGuildAppState) -> None:
    module = enable_module(app_state, "kidland", "KidLand")
    module.enabled = False

    updated_module = enable_module(app_state, "kidland", "KidLand Updated")

    assert updated_module is module
    assert updated_module.enabled is True
    assert updated_module.display_name.value == "KidLand Updated"
    assert len(app_state.family.enabled_modules) == 1


def test_configure_dashboard_widget_creates_widget(app_state: FamilyGuildAppState) -> None:
    child = add_child_member(app_state, "Alex")

    widget = configure_dashboard_widget(
        app_state,
        module_key="kidland",
        widget_key="famcoins_balance",
        visible_for_role="child",
        visible_for_member=child,
        position=2,
    )

    assert widget.module_key == "kidland"
    assert widget.widget_key == "famcoins_balance"
    assert widget.enabled is True
    assert widget.visible_for_role == "child"
    assert widget.visible_for_member is child
    assert widget.position == 2
    assert widget in app_state.family.dashboard_widgets


def test_configure_dashboard_widget_updates_existing_widget(app_state: FamilyGuildAppState) -> None:
    widget = configure_dashboard_widget(app_state, "kidland", "pending_approvals", position=2)

    updated_widget = configure_dashboard_widget(
        app_state,
        "kidland",
        "pending_approvals",
        enabled=False,
        visible_for_role="parent",
        position=1,
    )

    assert updated_widget is widget
    assert updated_widget.enabled is False
    assert updated_widget.visible_for_role == "parent"
    assert updated_widget.position == 1
    assert len(app_state.family.dashboard_widgets) == 1


def test_configure_dashboard_widget_rejects_unknown_visible_member(app_state: FamilyGuildAppState) -> None:
    unknown_child = Member("Riley", "child")

    with pytest.raises(ValueError, match="visible_for_member"):
        configure_dashboard_widget(
            app_state,
            "kidland",
            "famcoins_balance",
            visible_for_member=unknown_child,
        )
