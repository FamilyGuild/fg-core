"""Module registration models for FamilyGuild Core."""

from dataclasses import dataclass

import dbzero as db0
from dbzero_modelkit import ML_String


@db0.memo(id="/familyguild/core/ModuleRegistration")
@dataclass
class ModuleRegistration:
    """Module entry available to the FamilyGuild foundation shell."""

    module_key: str
    display_name: ML_String
    enabled: bool = True
    navigation_label: ML_String | None = None

    def __post_init__(self) -> None:
        if self.navigation_label is None:
            self.navigation_label = self.display_name
