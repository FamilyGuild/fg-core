"""Family and member models for trusted local switching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import dbzero as db0


@db0.memo(id="/familyguild/core/Family")
@dataclass
class Family:
    """One household identity inside the FamilyGuild app state."""

    household_key: str = "default"
    members: list[Member] = field(default_factory=list)
    enabled_modules: list[object] = field(default_factory=list)
    dashboard_widgets: list[object] = field(default_factory=list)


@db0.memo(id="/familyguild/core/Member")
@dataclass
class Member:
    """Family member visible in trusted member switching."""

    display_name: str
    role: str
    active: bool = True
    kid_profile_ref: str | None = None


@db0.memo(id="/familyguild/core/ActiveMemberState")
@dataclass
class ActiveMemberState:
    """Current trusted member selection for the local private MVP."""

    active_member: Member | None = None
    last_switched_at: datetime | None = None
