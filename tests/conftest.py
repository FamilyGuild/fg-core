from types import ModuleType

import pytest

import fg_core


@pytest.fixture
def fg_core_package() -> ModuleType:
    return fg_core
