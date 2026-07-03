"""Explicit commands that mutate FamilyGuild Core state."""

from datetime import UTC, datetime

import dbzero as db0
from dbzero_modelkit import LanguageCode, ML_String

from fg_core.models import (
    ActiveMemberState,
    CorePreferences,
    DashboardWidgetConfig,
    Family,
    FamilyGuildAppState,
    Member,
    ModuleRegistration,
)

SUPPORTED_LANGUAGES = {"en", "pl"}
SUPPORTED_MEMBER_ROLES = {"parent", "child"}


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
        ValueError: If a text field is empty or the language is unsupported.
    """

    family_display_name = _require_non_empty(
        family_display_name,
        "family_display_name",
    )
    currency_name = _require_non_empty(currency_name, "currency_name")
    household_key = _require_non_empty(household_key, "household_key")
    _validate_language_preference(language_preference)

    with db0.atomic():
        app_state = FamilyGuildAppState(
            family=Family(household_key),
            preferences=CorePreferences(
                family_display_name=family_display_name,
                currency_name=currency_name,
                language_preference=language_preference,
            ),
            active_member_state=ActiveMemberState(),
        )

    return app_state


def add_parent_member(app_state: FamilyGuildAppState, display_name: str) -> Member:
    """Add an active parent member to a family.

    Args:
        app_state: Root app state whose household should own the member.
        display_name: Member name shown in trusted switching.

    Returns:
        The created parent `Member`.

    Raises:
        ValueError: If the display name is empty.
    """

    return _add_member(app_state, display_name, "parent")


def add_child_member(
    app_state: FamilyGuildAppState,
    display_name: str,
    kid_profile_ref: str | None = None,
) -> Member:
    """Add an active child member to a family.

    Args:
        app_state: Root app state whose household should own the member.
        display_name: Member name shown in trusted switching.
        kid_profile_ref: Optional module-owned KidLand profile reference.

    Returns:
        The created child `Member`.

    Raises:
        ValueError: If the display name is empty.
    """

    return _add_member(app_state, display_name, "child", kid_profile_ref)


def switch_active_member(
    app_state: FamilyGuildAppState,
    member: Member,
    switched_at: datetime | None = None,
) -> ActiveMemberState:
    """Switch the trusted active member for the local MVP shell.

    Args:
        app_state: Root app state whose household members may be selected.
        member: Active family member to select.
        switched_at: Optional timestamp for deterministic callers or tests.

    Returns:
        The root-owned `ActiveMemberState` after the switch.

    Raises:
        ValueError: If the member does not belong to the family or is inactive.
    """

    if member not in app_state.family.members:
        raise ValueError("member must belong to the family")
    if not member.active:
        raise ValueError("inactive members cannot become active")

    with db0.atomic():
        active_state = app_state.active_member_state
        active_state.active_member = member
        active_state.last_switched_at = switched_at or datetime.now(UTC)

    return active_state


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
        ValueError: If the module key or label text is empty.
    """

    module_key = _require_non_empty(module_key, "module_key")
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
        ValueError: If keys are empty, role is unsupported, or member visibility
            references a member outside the family.
    """

    module_key = _require_non_empty(module_key, "module_key")
    widget_key = _require_non_empty(widget_key, "widget_key")
    if visible_for_role is not None:
        _validate_member_role(visible_for_role)
    if visible_for_member is not None and visible_for_member not in app_state.family.members:
        raise ValueError("visible_for_member must belong to the family")

    existing_widget = _find_widget(app_state.family, module_key, widget_key)

    with db0.atomic():
        if existing_widget is None:
            widget = DashboardWidgetConfig(
                module_key=module_key,
                widget_key=widget_key,
                enabled=enabled,
                visible_for_role=visible_for_role,
                visible_for_member=visible_for_member,
                position=position,
            )
            app_state.family.dashboard_widgets.append(widget)
        else:
            widget = existing_widget
            widget.enabled = enabled
            widget.visible_for_role = visible_for_role
            widget.visible_for_member = visible_for_member
            widget.position = position

    return widget


def _add_member(
    app_state: FamilyGuildAppState,
    display_name: str,
    role: str,
    kid_profile_ref: str | None = None,
) -> Member:
    display_name = _require_non_empty(display_name, "display_name")
    _validate_member_role(role)

    with db0.atomic():
        member = Member(display_name, role, active=True, kid_profile_ref=kid_profile_ref)
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


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _validate_language_preference(language_preference: str) -> None:
    if language_preference not in SUPPORTED_LANGUAGES:
        raise ValueError("language_preference must be 'en' or 'pl'")


def _validate_member_role(role: str) -> None:
    if role not in SUPPORTED_MEMBER_ROLES:
        raise ValueError("role must be 'parent' or 'child'")


def _to_ml_string(value: str | ML_String) -> ML_String:
    if isinstance(value, ML_String):
        return value
    return ML_String(_require_non_empty(value, "label"), _language_code("en"))


def _language_code(language: str):
    target_name = {"en": "LEN", "pl": "LPL"}[language]
    for language_code in LanguageCode.values():
        if str(language_code) == target_name:
            return language_code
    raise ValueError(f"unsupported language code: {language}")
