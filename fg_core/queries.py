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


def resolve_trusted_member(
    app_state: FamilyGuildAppState, member_id: str | None
) -> Member | None:
    """Resolve a client-selected identifier to an active household member.

    Args:
        app_state: Root app state whose household owns selectable members.
        member_id: dbzero UUID stored by one client context, or `None`.

    Returns:
        The active household `Member` with the identifier, or `None` when the
        identifier is absent, unknown, or belongs to an inactive member.
    """

    if not member_id:
        return None

    for member in app_state.family.members:
        if member.active and db0.uuid(member) == member_id:
            return member
    return None


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
