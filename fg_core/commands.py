"""Explicit commands that mutate FamilyGuild Core state."""

from __future__ import annotations

import dbzero as db0
from dbzero_modelkit import LanguageCode, ML_String

from fg_core.models import (
    DashboardWidgetConfig,
    Family,
    FamilyGuildAppState,
    Member,
    MemberRole,
    ModuleRegistration,
)

SUPPORTED_LANGUAGES = {"en", "pl"}
SUPPORTED_MEMBER_ROLES = {
    "parent": MemberRole.parent,
    "child": MemberRole.child,
}


def initialize_household(
    app_state: FamilyGuildAppState,
    family_display_name: str,
    parent_name: str,
    currency_name: str = "FamCoins",
    language_preference: str = "en",
) -> Member:
    """Configure an empty household and return its first parent atomically.

    Reject repeated setup even when the previous members are inactive. Existing
    registrations and the internal household key remain unchanged.
    """
    _validate_required_text(parent_name, "parent_name")
    with db0.atomic():
        if len(app_state.family.members):
            raise ValueError("Household already has members.")
        update_preferences(app_state, family_display_name, currency_name, language_preference)
        return add_parent_member(app_state, parent_name)


def update_preferences(
    app_state: FamilyGuildAppState,
    family_display_name: str,
    currency_name: str,
    language_preference: str,
) -> None:
    """Validate and atomically update family-facing preferences, not identity keys."""
    _validate_required_text(family_display_name, "family_display_name")
    _validate_required_text(currency_name, "currency_name")
    _validate_language_preference(language_preference)
    with db0.atomic():
        app_state.preferences.family_display_name = family_display_name
        app_state.preferences.currency_name = currency_name
        app_state.preferences.language_preference = language_preference


def rename_member(app_state: FamilyGuildAppState, member_id: str, display_name: str) -> None:
    """Rename a household member without changing identity or relationships."""
    _validate_required_text(display_name, "display_name")
    with db0.atomic():
        _managed_member(app_state, member_id).display_name = display_name


def set_member_active(app_state: FamilyGuildAppState, member_id: str, active: bool) -> None:
    """Change membership availability while preserving at least one active parent."""
    with db0.atomic():
        member = _managed_member(app_state, member_id)
        if member.active and member.role == MemberRole.parent and not active:
            if not any(
                other.active and other.role == MemberRole.parent and other != member
                for other in app_state.family.members
            ):
                raise ValueError("The last active parent cannot be deactivated.")
        member.active = active


def _managed_member(app_state: FamilyGuildAppState, member_id: str) -> Member:
    """Resolve an active or inactive management target within this household."""
    for member in app_state.family.members:
        if db0.uuid(member) == member_id:
            return member
    raise ValueError("Member does not belong to this household.")


def create_family(
    family_display_name: str,
    currency_name: str = "FamCoins",
    language_preference: str = "en",
    household_key: str = "default",
) -> FamilyGuildAppState:
    """Create the one-household root app state and preferences.

    Args:
        family_display_name: Family-facing display name stored in core preferences.
        currency_name: Family currency label stored in core preferences.
        language_preference: Initial language preference, currently `en` or `pl`.
        household_key: Stable internal key for the household.

    Returns:
        The singleton `FamilyGuildAppState` root.

    Raises:
        ValueError: If a required name or household key is blank, or the language
            is unsupported.
    """

    _validate_required_text(family_display_name, "family_display_name")
    _validate_required_text(currency_name, "currency_name")
    _validate_required_text(household_key, "household_key")
    _validate_language_preference(language_preference)

    with db0.atomic():
        app_state = FamilyGuildAppState()
        app_state.family.household_key = household_key
        app_state.preferences.family_display_name = family_display_name
        app_state.preferences.currency_name = currency_name
        app_state.preferences.language_preference = language_preference

    return app_state


def add_parent_member(app_state: FamilyGuildAppState, display_name: str) -> Member:
    """Add an active parent member to a family.

    Args:
        app_state: Root app state whose household should own the member.
        display_name: Member name shown in trusted switching.

    Returns:
        The created parent `Member`.

    Raises:
        ValueError: If the display name is blank.
    """

    return _add_member(app_state, display_name, MemberRole.parent)


def add_child_member(
    app_state: FamilyGuildAppState,
    display_name: str,
    kid_profile_uuid: str | None = None,
) -> Member:
    """Add an active child member to a family.

    Args:
        app_state: Root app state whose household should own the member.
        display_name: Member name shown in trusted switching.
        kid_profile_uuid: Optional dbzero UUID handle for a module-owned KidLand profile.

    Returns:
        The created child `Member`.

    Raises:
        ValueError: If the display name is blank.
    """

    return _add_member(app_state, display_name, MemberRole.child, kid_profile_uuid)


def enable_module(
    app_state: FamilyGuildAppState,
    module_key: str,
    display_name: str | ML_String,
    navigation_label: str | ML_String | None = None,
) -> ModuleRegistration:
    """Create or re-enable a module registration.

    Args:
        app_state: Root app state whose household owns module registrations.
        module_key: Stable internal module key, for example `kidland`.
        display_name: User-facing module label as plain text or `ML_String`.
        navigation_label: Optional navigation label as plain text or `ML_String`.

    Returns:
        The created or updated `ModuleRegistration`.

    Raises:
        ValueError: If the module key or a supplied label is blank.
    """

    _validate_required_text(module_key, "module_key")
    _validate_required_text(display_name, "display_name")
    if navigation_label is not None:
        _validate_required_text(navigation_label, "navigation_label")
    existing_module = _find_module(app_state.family, module_key)

    with db0.atomic():
        display_name_text = _to_ml_string(display_name)
        navigation_label_text = (
            _to_ml_string(navigation_label)
            if navigation_label is not None
            else display_name_text
        )

        if existing_module is None:
            module = ModuleRegistration(
                module_key=module_key,
                display_name=display_name_text,
                enabled=True,
                navigation_label=navigation_label_text,
            )
            app_state.family.enabled_modules.append(module)
        else:
            module = existing_module
            module.display_name = display_name_text
            module.navigation_label = navigation_label_text
            module.enabled = True

    return module


def configure_dashboard_widget(
    app_state: FamilyGuildAppState,
    module_key: str,
    widget_key: str,
    enabled: bool = True,
    visible_for_role: str | None = None,
    visible_for_member: Member | None = None,
    position: int = 0,
) -> DashboardWidgetConfig:
    """Create or update a FamilyGuild general dashboard widget config.

    Args:
        app_state: Root app state whose household owns dashboard configuration.
        module_key: Stable internal key of the module providing the widget.
        widget_key: Stable internal widget key.
        enabled: Whether the widget should appear on the general dashboard.
        visible_for_role: Optional role visibility filter, `parent` or `child`.
        visible_for_member: Optional member-specific visibility filter.
        position: Display order for enabled widgets.

    Returns:
        The created or updated `DashboardWidgetConfig`.

    Raises:
        ValueError: If a module or widget key is blank, the role is unsupported,
            or member visibility references a member outside the family.
    """

    _validate_required_text(module_key, "module_key")
    _validate_required_text(widget_key, "widget_key")
    visible_for_role_value = (
        _coerce_member_role(visible_for_role)
        if visible_for_role is not None
        else None
    )
    if visible_for_member is not None:
        member_uuid = db0.uuid(visible_for_member)
        if not any(db0.uuid(candidate) == member_uuid for candidate in app_state.family.members):
            raise ValueError("visible_for_member must belong to the family")

    existing_widget = _find_widget(app_state.family, module_key, widget_key)

    with db0.atomic():
        if existing_widget is None:
            widget = DashboardWidgetConfig(
                module_key=module_key,
                widget_key=widget_key,
                enabled=enabled,
                visible_for_role=visible_for_role_value,
                visible_for_member=visible_for_member,
                position=position,
            )
            app_state.family.dashboard_widgets.append(widget)
        else:
            widget = existing_widget
            widget.enabled = enabled
            widget.visible_for_role = visible_for_role_value
            widget.visible_for_member = visible_for_member
            widget.position = position

    return widget


def _add_member(
    app_state: FamilyGuildAppState,
    display_name: str,
    role: MemberRole,
    kid_profile_uuid: str | None = None,
) -> Member:
    _validate_required_text(display_name, "display_name")
    role = _coerce_member_role(role)

    with db0.atomic():
        member = Member(display_name, role, active=True, kid_profile_uuid=kid_profile_uuid)
        app_state.family.members.append(member)

    return member


def _find_module(family: Family, module_key: str) -> ModuleRegistration | None:
    for module in family.enabled_modules:
        if module.module_key == module_key:
            return module
    return None


def _find_widget(
    family: Family,
    module_key: str,
    widget_key: str,
) -> DashboardWidgetConfig | None:
    for widget in family.dashboard_widgets:
        if widget.module_key == module_key and widget.widget_key == widget_key:
            return widget
    return None


def _validate_required_text(value: str | ML_String, field: str) -> None:
    """Reject blank command input without normalizing the stored value."""
    text = value.value if isinstance(value, ML_String) else value
    if not text.strip():
        raise ValueError(f"{field} must not be blank")


def _validate_language_preference(language_preference: str) -> None:
    if language_preference not in SUPPORTED_LANGUAGES:
        raise ValueError("language_preference must be 'en' or 'pl'")


def _coerce_member_role(role: str | MemberRole) -> MemberRole:
    if role in MemberRole.values():
        return role
    if isinstance(role, str):
        if role in SUPPORTED_MEMBER_ROLES:
            return SUPPORTED_MEMBER_ROLES[role]

    if isinstance(role, str):
        raise ValueError("role must be 'parent' or 'child'")
    raise ValueError("role must be MemberRole.parent or MemberRole.child")


def _to_ml_string(value: str | ML_String) -> ML_String:
    if isinstance(value, ML_String):
        return value
    return ML_String(value, _language_code("en"))


def _language_code(language: str):
    target_name = {"en": "LEN", "pl": "LPL"}[language]
    for language_code in LanguageCode.values():
        if str(language_code) == target_name:
            return language_code
    raise ValueError(f"unsupported language code: {language}")
