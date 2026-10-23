"""Behavioral tests for household bootstrap and management commands."""

from pathlib import Path

import dbzero as db0
import pytest

from fg_core.commands import (
    add_parent_member, initialize_household, rename_member,
    set_member_active, update_preferences,
)
from fg_core.models import FamilyGuildAppState, Member


def test_bootstrap_is_one_time(app_state: FamilyGuildAppState) -> None:
    """Bootstrap creates one parent and rejects a stale second submission."""
    parent = initialize_household(app_state, "Home", "First", "Stars", "pl")
    assert parent.active
    assert app_state.preferences.family_display_name == "Home"
    assert app_state.preferences.language_preference == "pl"
    with pytest.raises(ValueError):
        initialize_household(app_state, "Overwrite", "Other")
    assert len(app_state.family.members) == 1
    assert app_state.preferences.family_display_name == "Home"


def test_invalid_bootstrap_has_no_partial_changes(app_state: FamilyGuildAppState) -> None:
    """Invalid first-parent input does not overwrite household preferences."""
    with pytest.raises(ValueError):
        initialize_household(app_state, "Changed", " ")
    assert app_state.preferences.family_display_name == "Test Family"
    assert len(app_state.family.members) == 0


def test_member_lifecycle(app_state: FamilyGuildAppState, parent_member: Member) -> None:
    """Renaming and reactivation retain identity; last-parent removal fails."""
    member_id = db0.uuid(parent_member)
    rename_member(app_state, member_id, "Renamed")
    assert db0.uuid(parent_member) == member_id
    assert parent_member.display_name == "Renamed"
    with pytest.raises(ValueError):
        set_member_active(app_state, member_id, False)
    add_parent_member(app_state, "Other")
    set_member_active(app_state, member_id, False)
    assert not parent_member.active
    set_member_active(app_state, member_id, True)
    assert parent_member.active


def test_unknown_target_and_invalid_preferences(
    app_state: FamilyGuildAppState,
) -> None:
    """Reject foreign targets and invalid preferences without partial writes."""
    with pytest.raises(ValueError):
        rename_member(app_state, "unknown", "Name")
    with pytest.raises(ValueError):
        update_preferences(app_state, "Changed", "Stars", "de")
    assert app_state.preferences.family_display_name == "Test Family"
    update_preferences(app_state, "Home", "Stars", "pl")
    assert app_state.preferences.currency_name == "Stars"


def test_management_survives_reopen(
    app_state: FamilyGuildAppState, dbzero_state: Path,
) -> None:
    """Autocommit on close preserves setup, preferences and member identities."""
    parent = initialize_household(app_state, "Home", "First", "Stars", "pl")
    member_id = db0.uuid(parent)
    rename_member(app_state, member_id, "Renamed")
    db0.close()
    db0.init(str(dbzero_state / "db0"), prefix="core")
    restored = FamilyGuildAppState()
    assert db0.uuid(restored.family.members[0]) == member_id
    assert restored.family.members[0].display_name == "Renamed"
    assert restored.preferences.currency_name == "Stars"
    assert restored.preferences.language_preference == "pl"
