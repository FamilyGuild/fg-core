from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import dbzero as db0
import pytest

import fg_core
from fg_core.commands import (
    add_child_member,
    add_parent_member,
    create_family,
    enable_module,
)
from fg_core.models import CorePreferences, Family, FamilyGuildAppState, Member, ModuleRegistration


@pytest.fixture(autouse=True)
def dbzero_state(tmp_path: Path) -> Iterator[Path]:
    db0.init(str(tmp_path / "db0"), prefix="core")
    yield tmp_path
    db0.close()


@pytest.fixture
def fg_core_package() -> ModuleType:
    return fg_core


@pytest.fixture
def app_state() -> FamilyGuildAppState:
    return create_family("Test Family")


@pytest.fixture
def family(app_state: FamilyGuildAppState) -> Family:
    return app_state.family


@pytest.fixture
def core_preferences(app_state: FamilyGuildAppState) -> CorePreferences:
    return app_state.preferences


@pytest.fixture
def parent_member(app_state: FamilyGuildAppState) -> Member:
    return add_parent_member(app_state, "Parent")


@pytest.fixture
def child_member(app_state: FamilyGuildAppState) -> Member:
    return add_child_member(app_state, "Child")


@pytest.fixture
def duplicate_child_members(app_state: FamilyGuildAppState) -> tuple[Member, Member]:
    return add_child_member(app_state, "Alex"), add_child_member(app_state, "Alex")


@pytest.fixture
def kidland_module(app_state: FamilyGuildAppState) -> ModuleRegistration:
    return enable_module(app_state, "kidland", "KidLand")
