"""General dashboard configuration models for FamilyGuild Core."""

from __future__ import annotations

from dataclasses import dataclass

import dbzero as db0

from fg_core.models.family import Member


@db0.memo(id="/familyguild/core/DashboardWidgetConfig")
@dataclass
class DashboardWidgetConfig:
    """Selected widget configuration for the FamilyGuild general dashboard."""

    module_key: str
    widget_key: str
    enabled: bool = True
    visible_for_role: str | None = None
    visible_for_member: Member | None = None
    position: int = 0
