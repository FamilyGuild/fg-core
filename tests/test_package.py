from dataclasses import is_dataclass
from types import ModuleType

from fg_core.models import (
    ActiveMemberState,
    CorePreferences,
    DashboardWidgetConfig,
    Family,
    FamilyGuildAppState,
    Member,
    ModuleRegistration,
)


def test_package_is_importable(fg_core_package: ModuleType) -> None:
    assert fg_core_package.PACKAGE_NAME == "fg_core"


def test_documented_model_package_exports_core_models() -> None:
    assert FamilyGuildAppState.__module__ == "fg_core.models.app_state"
    assert Family.__module__ == "fg_core.models.family"
    assert Member.__module__ == "fg_core.models.family"
    assert ActiveMemberState.__module__ == "fg_core.models.family"
    assert CorePreferences.__module__ == "fg_core.models.preferences"
    assert ModuleRegistration.__module__ == "fg_core.models.modules"
    assert DashboardWidgetConfig.__module__ == "fg_core.models.dashboard"


def test_core_models_are_dataclasses() -> None:
    assert is_dataclass(FamilyGuildAppState)
    assert is_dataclass(Family)
    assert is_dataclass(Member)
    assert is_dataclass(ActiveMemberState)
    assert is_dataclass(CorePreferences)
    assert is_dataclass(ModuleRegistration)
    assert is_dataclass(DashboardWidgetConfig)
