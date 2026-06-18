from types import ModuleType


def test_package_is_importable(fg_core_package: ModuleType) -> None:
    assert fg_core_package.PACKAGE_NAME == "fg_core"
