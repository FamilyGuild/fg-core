from pathlib import Path

import dbzero as db0
import pytest
from dbzero_modelkit import LanguageCode, ML_String

from fg_core.commands import (
    add_child_member,
    add_parent_member,
    configure_dashboard_widget,
    create_family,
    enable_module,
)
from fg_core.models import CorePreferences, FamilyGuildAppState, Member, MemberRole


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
@pytest.mark.parametrize("field", ["family_display_name", "currency_name", "household_key"])
def test_create_family_rejects_blank_inputs(field: str, blank: str) -> None:
    arguments = {"family_display_name": "Guild House", field: blank}
    with pytest.raises(ValueError, match=field):
        create_family(**arguments)

    state = create_family("Valid Family")
    assert state.preferences.family_display_name == "Valid Family"
    assert state.family.household_key == "default"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
@pytest.mark.parametrize("child", [False, True])
def test_add_member_rejects_blank_name(
    app_state: FamilyGuildAppState, blank: str, child: bool
) -> None:
    parent = add_parent_member(app_state, "Ada")
    command = add_child_member if child else add_parent_member
    with pytest.raises(ValueError, match="display_name"):
        command(app_state, blank)
    assert [db0.uuid(member) for member in app_state.family.members] == [db0.uuid(parent)]


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
@pytest.mark.parametrize("field", ["module_key", "display_name", "navigation_label"])
@pytest.mark.parametrize("existing", [False, True])
def test_enable_module_rejects_blank_inputs(
    app_state: FamilyGuildAppState, blank: str, field: str, existing: bool
) -> None:
    if existing:
        module = enable_module(app_state, "kidland", "Original", "Navigation")
        module.enabled = False
    arguments = {"module_key": "kidland", "display_name": "Updated", field: blank}
    with pytest.raises(ValueError, match=field):
        enable_module(app_state, **arguments)
    assert len(app_state.family.enabled_modules) == int(existing)
    if existing:
        assert module.enabled is False
        assert module.display_name.value == "Original"
        assert module.navigation_label.value == "Navigation"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
@pytest.mark.parametrize("field", ["display_name", "navigation_label"])
@pytest.mark.parametrize("existing", [False, True])
def test_enable_module_rejects_blank_multilingual_labels(
    app_state: FamilyGuildAppState, blank: str, field: str, existing: bool
) -> None:
    if existing:
        module = enable_module(app_state, "kidland", "Original", "Navigation")
        module.enabled = False
    label = ML_String(blank, LanguageCode.LEN)
    with pytest.raises(ValueError, match=field):
        enable_module(
            app_state, "kidland", label if field == "display_name" else "Updated",
            navigation_label=label if field == "navigation_label" else None,
        )
    assert len(app_state.family.enabled_modules) == int(existing)
    if existing:
        assert module.enabled is False
        assert module.display_name.value == "Original"
        assert module.navigation_label.value == "Navigation"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
@pytest.mark.parametrize("field", ["module_key", "widget_key"])
def test_widget_rejects_blank_identifiers(
    app_state: FamilyGuildAppState, blank: str, field: str
) -> None:
    widget = configure_dashboard_widget(app_state, "kidland", "balance", position=2)
    arguments = {"module_key": "kidland", "widget_key": "balance", field: blank}
    with pytest.raises(ValueError, match=field):
        configure_dashboard_widget(app_state, **arguments, enabled=False, position=9)
    assert len(app_state.family.dashboard_widgets) == 1
    assert widget.enabled is True
    assert widget.position == 2


def test_commands_preserve_nonblank_text() -> None:
    state = create_family(" Family ", currency_name=" Coins ", household_key=" home ")
    assert state.preferences.family_display_name == " Family "
    assert state.preferences.currency_name == " Coins "
    assert state.family.household_key == " home "
    assert add_parent_member(state, " Ada ").display_name == " Ada "
    assert add_child_member(state, " Alex ").display_name == " Alex "
    label = ML_String(" Module ", LanguageCode.LEN)
    module = enable_module(state, " module ", label)
    assert module.module_key == " module "
    assert module.display_name.value == " Module "
    assert db0.uuid(module.navigation_label) == db0.uuid(label)
    widget = configure_dashboard_widget(state, " module ", " widget ")
    assert widget.module_key == " module "
    assert widget.widget_key == " widget "


def test_create_family_initializes_singleton_root() -> None:
    app_state = create_family("Guild House")

    assert isinstance(app_state, FamilyGuildAppState)
    assert app_state is FamilyGuildAppState()
    assert app_state.family.household_key == "default"
    assert isinstance(app_state.preferences, CorePreferences)
    assert app_state.preferences.family_display_name == "Guild House"
    assert app_state.preferences.currency_name == "FamCoins"
    assert app_state.preferences.language_preference == "en"
    assert not hasattr(app_state, "active_member_state")


def test_create_family_initializes_default_root_created_during_startup() -> None:
    default_state = FamilyGuildAppState()

    app_state = create_family(
        "Guild House",
        currency_name="Stars",
        language_preference="pl",
        household_key="guild-house",
    )

    assert app_state is default_state
    assert app_state.family.household_key == "guild-house"
    assert app_state.preferences.family_display_name == "Guild House"
    assert app_state.preferences.currency_name == "Stars"
    assert app_state.preferences.language_preference == "pl"


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
    assert parent.role == MemberRole.parent
    assert str(parent.role) == "parent"
    assert parent.active is True
    assert parent in app_state.family.members


def test_add_child_member(app_state: FamilyGuildAppState) -> None:
    child = add_child_member(app_state, "Alex", kid_profile_uuid="kid-profile-1")

    assert child.display_name == "Alex"
    assert child.role == MemberRole.child
    assert str(child.role) == "child"
    assert child.active is True
    assert child.kid_profile_uuid == "kid-profile-1"
    assert child in app_state.family.members


@pytest.mark.parametrize("existing", [False, True])
def test_widget_rejects_value_equal_nonmember(
    app_state: FamilyGuildAppState, existing: bool
) -> None:
    child = add_child_member(app_state, "Alex")
    detached = Member("Alex", MemberRole.child)
    assert detached == child
    assert db0.uuid(detached) != db0.uuid(child)
    if existing:
        configure_dashboard_widget(
            app_state, "kidland", "balance", visible_for_member=child, position=2
        )

    with pytest.raises(ValueError, match="visible_for_member"):
        configure_dashboard_widget(
            app_state, "kidland", "balance", enabled=False,
            visible_for_member=detached, position=9,
        )

    widgets = app_state.family.dashboard_widgets
    assert len(widgets) == (1 if existing else 0)
    if existing:
        assert db0.uuid(widgets[0].visible_for_member) == db0.uuid(child)
        assert widgets[0].enabled is True
        assert widgets[0].position == 2


def test_widget_command_accepts_refetched_member_after_reopen(
    app_state: FamilyGuildAppState, dbzero_state: Path
) -> None:
    child = add_child_member(app_state, "Alex")
    member_uuid = db0.uuid(child)
    db0.commit()
    db0.close()
    db0.init(str(dbzero_state / "db0"), prefix="core")
    restored_state = FamilyGuildAppState()
    restored_member = db0.fetch(member_uuid, Member)

    widget = configure_dashboard_widget(
        restored_state, "kidland", "balance", visible_for_member=restored_member
    )

    assert db0.uuid(widget.visible_for_member) == member_uuid


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
    assert widget.visible_for_role == MemberRole.child
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
    assert updated_widget.visible_for_role == MemberRole.parent
    assert updated_widget.position == 1
    assert len(app_state.family.dashboard_widgets) == 1


def test_configure_dashboard_widget_rejects_unknown_visible_member(app_state: FamilyGuildAppState) -> None:
    unknown_child = Member("Riley", MemberRole.child)

    with pytest.raises(ValueError, match="visible_for_member"):
        configure_dashboard_widget(
            app_state,
            "kidland",
            "famcoins_balance",
            visible_for_member=unknown_child,
        )


def test_configure_dashboard_widget_rejects_unknown_visible_role(app_state: FamilyGuildAppState) -> None:
    with pytest.raises(ValueError, match="role"):
        configure_dashboard_widget(
            app_state,
            "kidland",
            "famcoins_balance",
            visible_for_role="manager",
        )
