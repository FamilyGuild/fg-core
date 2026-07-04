"""Read-only helpers for FamilyGuild Core state."""

from typing import Any

import dbzero as db0

from fg_core.models import (
    CorePreferences,
    DashboardWidgetConfig,
    FamilyGuildAppState,
    Member,
    ModuleRegistration,
)


def get_app_state() -> FamilyGuildAppState:
    """Return the singleton one-household app state root.

    Returns:
        The singleton `FamilyGuildAppState` object.
    """

    return FamilyGuildAppState()


def get_family_summary(app_state: FamilyGuildAppState) -> dict[str, Any]:
    """Return a compact family/preferences summary for the workspace.

    Args:
        app_state: Root app state to summarize.

    Returns:
        Dictionary with household key, preference labels, and member count.
    """

    family = app_state.family
    preferences = app_state.preferences

    return {
        "household_key": family.household_key,
        "family_display_name": preferences.family_display_name,
        "currency_name": preferences.currency_name,
        "language_preference": preferences.language_preference,
        "member_count": len(family.members),
    }


def get_core_preferences(app_state: FamilyGuildAppState) -> CorePreferences:
    """Return persisted foundation preferences for the first workspace.

    Args:
        app_state: Root app state that owns preferences.

    Returns:
        The `CorePreferences` object owned by the root app state.
    """

    return app_state.preferences


def get_active_member(app_state: FamilyGuildAppState) -> Member | None:
    """Return the current trusted member, if one has been selected.

    Args:
        app_state: Root app state that owns active member state.

    Returns:
        The selected `Member`, or `None` when no member is active.
    """

    return app_state.active_member_state.active_member


def get_active_member_uuid(app_state: FamilyGuildAppState) -> str | None:
    """Return the dbzero UUID for the current trusted member when selected.

    Args:
        app_state: Root app state that owns active member state.

    Returns:
        The selected member's dbzero UUID, or `None` when no member is active.
    """

    active_member = get_active_member(app_state)
    if active_member is None:
        return None
    return db0.uuid(active_member)


def get_member_switcher_options(app_state: FamilyGuildAppState) -> list[Member]:
    """Return active family members available for trusted switching.

    Args:
        app_state: Root app state whose household members should be listed.

    Returns:
        Active members that may be selected in trusted switching.
    """

    return [member for member in app_state.family.members if member.active]


def get_enabled_modules(app_state: FamilyGuildAppState) -> list[ModuleRegistration]:
    """Return enabled module registrations.

    Args:
        app_state: Root app state whose household modules should be listed.

    Returns:
        Enabled module registrations.
    """

    return [module for module in app_state.family.enabled_modules if module.enabled]


def get_visible_navigation(app_state: FamilyGuildAppState) -> list[ModuleRegistration]:
    """Return module entries visible in foundation navigation.

    Args:
        app_state: Root app state whose navigation should be listed.

    Returns:
        Enabled module registrations visible in navigation.
    """

    return get_enabled_modules(app_state)


def get_general_dashboard_config(app_state: FamilyGuildAppState) -> list[DashboardWidgetConfig]:
    """Return enabled dashboard widgets ordered for display.

    Args:
        app_state: Root app state whose dashboard configuration should be listed.

    Returns:
        Enabled dashboard widgets ordered by position.
    """

    return sorted(
        [widget for widget in app_state.family.dashboard_widgets if widget.enabled],
        key=lambda widget: widget.position,
    )
