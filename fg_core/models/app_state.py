"""Singleton root state for one FamilyGuild household app instance."""

from __future__ import annotations

from dataclasses import dataclass, field

import dbzero as db0

from fg_core.models.family import ActiveMemberState, Family
from fg_core.models.preferences import CorePreferences


@db0.memo(singleton=True, id="/familyguild/core/FamilyGuildAppState")
@dataclass
class FamilyGuildAppState:
    """Singleton root for one FamilyGuild app instance and household."""

    family: Family = field(default_factory=Family)
    preferences: CorePreferences = field(default_factory=CorePreferences)
    active_member_state: ActiveMemberState = field(default_factory=ActiveMemberState)
