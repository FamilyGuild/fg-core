"""Family and member models for trusted local switching."""

from __future__ import annotations

from dataclasses import dataclass, field

import dbzero as db0


@db0.enum(values=["parent", "child"])
class MemberRole:
    """Constrained persisted roles for trusted member switching."""


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
    role: MemberRole
    active: bool = True
    kid_profile_uuid: str | None = None
